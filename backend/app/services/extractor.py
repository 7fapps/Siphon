import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

import yt_dlp
from playwright.async_api import async_playwright, Page, BrowserContext

from app.config import get_settings
from app.services.proxy import get_proxy_wrapper
from app.models.schemas import FormatInfo, ProbeResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class StealthExtractor:
    """
    Core extraction engine using Playwright with stealth patches
    and yt-dlp for format discovery. Intercepts network traffic to
    locate hidden streaming manifests (.m3u8, .mpd) before falling
    back to yt-dlp's native page analysis.
    """

    # Stealth evasion scripts injected before any page scripts run
    _STEALTH_SCRIPTS = [
        # Remove navigator.webdriver
        """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        """,
        # Patch navigator.plugins / mimeTypes
        """
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => [1, 2, 3, 4, 5],
        });
        """,
        # Override permissions query to auto-allow
        """
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
        );
        """,
        # Hide Playwright-specific properties
        """
        delete navigator.__proto__.webdriver;
        """,
        # Patch chrome runtime
        """
        window.chrome = { runtime: {} };
        """,
        # Fake Chrome plugins
        """
        Object.defineProperty(navigator, 'plugins', {
            get: function() {
                return [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin', description: 'Native Client' }
                ];
            }
        });
        """,
        # Fake languages
        """
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        """,
    ]

    def __init__(self):
        self.proxy = get_proxy_wrapper()
        self._intercepted_urls: List[str] = []

    async def _launch_stealth_context(self, playwright) -> BrowserContext:
        """Launch a stealth-hardened browser context."""
        browser = await playwright.chromium.launch(
            headless=settings.playwright_headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--window-size=1920,1080",
                "--start-maximized",
            ],
        )
        
        context_kwargs = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": [],
            "color_scheme": "light",
            "java_script_enabled": True,
            "bypass_csp": True,
        }
        
        if self.proxy.is_configured:
            context_kwargs["proxy"] = self.proxy.playwright_proxy()
        
        context = await browser.new_context(**context_kwargs)
        
        # Inject stealth scripts on every new page
        await context.add_init_script("\n".join(self._STEALTH_SCRIPTS))
        
        return context, browser

    async def _intercept_media(self, page: Page):
        """Intercept network requests to capture streaming manifest URLs."""
        self._intercepted_urls = []
        
        async def handle_route(route, request):
            url = request.url
            # Capture media manifests and raw media
            if any(ext in url.lower() for ext in ['.m3u8', '.mpd', '.m3u', '.mp4', '.webm', '.ts', '.dash', '.ism']):
                self._intercepted_urls.append(url)
                logger.info(f"Intercepted media URL: {url}")
            await route.continue_()
        
        await page.route("**/*", handle_route)

    async def probe(self, target_url: str) -> ProbeResponse:
        """
        Two-phase extraction:
        1. Playwright stealth page load + network interception
        2. yt-dlp format extraction (download=False)
        """
        logger.info(f"[probe] Starting extraction for {target_url}")
        
        # Phase 1: Stealth browser reconnaissance
        intercepted_manifests: List[str] = []
        try:
            async with async_playwright() as p:
                context, browser = await self._launch_stealth_context(p)
                page = await context.new_page()
                await self._intercept_media(page)
                
                try:
                    await page.goto(
                        target_url,
                        wait_until="networkidle",
                        timeout=settings.playwright_timeout,
                    )
                    # Wait a bit for lazy-loaded media players
                    await asyncio.sleep(2)
                    
                    # Try to trigger video load by scrolling or clicking play
                    try:
                        video = await page.query_selector("video")
                        if video:
                            await video.evaluate("el => el.play().catch(() => {})")
                            await asyncio.sleep(2)
                    except Exception as e:
                        logger.debug(f"Video trigger attempt failed: {e}")
                    
                    intercepted_manifests = list(dict.fromkeys(self._intercepted_urls))  # dedupe
                    logger.info(f"[probe] Intercepted {len(intercepted_manifests)} media URLs")
                    
                except Exception as e:
                    logger.warning(f"[probe] Playwright navigation error: {e}")
                finally:
                    await context.close()
                    await browser.close()
        except Exception as e:
            logger.warning(f"[probe] Playwright setup error: {e}")
        
        # Phase 2: yt-dlp format extraction
        formats = await self._extract_formats_with_ytdlp(target_url, intercepted_manifests)
        
        # Build unique height list (sorted ascending)
        heights = sorted({f.height for f in formats if f.height > 0})
        
        return ProbeResponse(
            url=target_url,
            title=formats[0].quality if formats else None,  # yt-dlp provides title separately
            formats=formats,
            heights=heights,
            message="success" if formats else "no_formats_found",
        )

    async def _extract_formats_with_ytdlp(
        self, target_url: str, intercepted_manifests: List[str]
    ) -> List[FormatInfo]:
        """
        Run yt-dlp --list-formats to extract all available video formats.
        Uses intercepted manifests as hints if the direct URL extraction fails.
        """
        loop = asyncio.get_event_loop()
        
        # Try direct URL first
        info = await loop.run_in_executor(
            None, self._ytdlp_extract_info, target_url
        )
        
        # If direct fails and we have intercepted manifests, try those
        if not info and intercepted_manifests:
            for manifest_url in intercepted_manifests[:3]:  # Try top 3
                logger.info(f"[probe] Trying intercepted manifest: {manifest_url}")
                info = await loop.run_in_executor(
                    None, self._ytdlp_extract_info, manifest_url
                )
                if info:
                    break
        
        if not info:
            logger.error("[probe] yt-dlp could not extract any formats")
            return []
        
        title = info.get("title")
        thumbnail = info.get("thumbnail")
        duration = info.get("duration")
        
        formats = []
        for fmt in info.get("formats", []):
            height = fmt.get("height") or 0
            if height == 0:
                continue
            formats.append(FormatInfo(
                format_id=fmt.get("format_id", ""),
                height=height,
                width=fmt.get("width") or 0,
                ext=fmt.get("ext", ""),
                vcodec=fmt.get("vcodec") or "none",
                acodec=fmt.get("acodec") or "none",
                abr=fmt.get("abr"),
                vbr=fmt.get("vbr"),
                filesize=fmt.get("filesize"),
                filesize_approx=fmt.get("filesize_approx"),
                video_ext=fmt.get("video_ext"),
                audio_ext=fmt.get("audio_ext"),
                quality=fmt.get("quality") or fmt.get("format_note"),
            ))
        
        return formats

    def _ytdlp_extract_info(self, url: str) -> Optional[Dict[str, Any]]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "best",
            "listformats": False,
            "skip_download": True,
            "extract_flat": False,
            "forcejson": True,
            "dump_single_json": False,
        }
        from app.services.proxy_pool import get_proxy_pool
        pool = get_proxy_pool()
        proxy = pool.get_random() if pool.has_proxies else None
        if proxy:
            ydl_opts["proxy"] = proxy
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            logger.warning(f"[ytdlp] Extraction failed for {url}: {e}")
            return None

    def _ytdlp_extract_audio_info(self, url: str) -> Optional[Dict[str, Any]]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio/best",
            "listformats": False,
            "skip_download": True,
            "extract_flat": False,
            "forcejson": True,
            "dump_single_json": False,
        }
        from app.services.proxy_pool import get_proxy_pool
        pool = get_proxy_pool()
        proxy = pool.get_random() if pool.has_proxies else None
        if proxy:
            ydl_opts["proxy"] = proxy
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            logger.warning(f"[ytdlp] Audio extraction failed for {url}: {e}")
            return None

    async def probe_audio(self, target_url: str) -> ProbeResponse:
        logger.info(f"[probe_audio] Starting audio extraction for {target_url}")
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, self._ytdlp_extract_audio_info, target_url)
        if not info:
            return ProbeResponse(url=target_url, formats=[], heights=[], message="no_audio_found")
        formats = []
        for fmt in info.get("formats", []):
            abr = fmt.get("abr") or 0
            if abr == 0 and fmt.get("acodec") != "none":
                abr = fmt.get("tbr") or 0
            formats.append(FormatInfo(
                format_id=fmt.get("format_id", ""),
                height=0,
                width=0,
                ext=fmt.get("ext", ""),
                vcodec="none",
                acodec=fmt.get("acodec") or "none",
                abr=abr if abr > 0 else None,
                vbr=None,
                filesize=fmt.get("filesize"),
                filesize_approx=fmt.get("filesize_approx"),
                video_ext=fmt.get("video_ext"),
                audio_ext=fmt.get("audio_ext"),
                quality=fmt.get("quality") or fmt.get("format_note") or f"{int(abr)}kbps",
            ))
        # Sort by bitrate descending
        formats.sort(key=lambda f: f.abr or 0, reverse=True)
        return ProbeResponse(
            url=target_url,
            title=info.get("title"),
            thumbnail=info.get("thumbnail"),
            duration=info.get("duration"),
            formats=formats,
            heights=[int(f.abr) for f in formats if f.abr],
            message="success" if formats else "no_audio_found",
        )


_extractor: Optional[StealthExtractor] = None

def get_extractor() -> StealthExtractor:
    global _extractor
    if _extractor is None:
        _extractor = StealthExtractor()
    return _extractor
