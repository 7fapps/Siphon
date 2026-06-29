from typing import Optional, Dict, Any
from app.config import get_settings
import asyncio
import httpx

class ProxyWrapper:
    """
    Configurable proxy wrapper for routing yt-dlp and HTTP requests
    through an upstream proxy. Supports HTTP/HTTPS/SOCKS proxies.
    """
    
    def __init__(self):
        self._settings = get_settings()
        self._proxy_url = self._settings.proxy_url
    
    @property
    def proxy_url(self) -> Optional[str]:
        return self._proxy_url
    
    @property
    def is_configured(self) -> bool:
        return self._proxy_url is not None and len(self._proxy_url.strip()) > 0
    
    def yt_dlp_proxy_args(self) -> list[str]:
        """Return yt-dlp CLI args for proxy routing."""
        if not self.is_configured:
            return []
        return ["--proxy", self._proxy_url]
    
    def httpx_proxies(self) -> Optional[Dict[str, str]]:
        """Return httpx-compatible proxy dict."""
        if not self.is_configured:
            return None
        return {
            "http://": self._proxy_url,
            "https://": self._proxy_url,
        }
    
    def playwright_proxy(self) -> Optional[Dict[str, Any]]:
        """Return Playwright proxy config dict."""
        if not self.is_configured:
            return None
        parsed = self._parse_proxy_url(self._proxy_url)
        proxy_cfg = {
            "server": f"{parsed['scheme']}://{parsed['host']}:{parsed['port']}",
        }
        if parsed.get("username"):
            proxy_cfg["username"] = parsed["username"]
        if parsed.get("password"):
            proxy_cfg["password"] = parsed["password"]
        return proxy_cfg
    
    @staticmethod
    def _parse_proxy_url(url: str) -> Dict[str, Any]:
        """Parse proxy URL into components."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return {
            "scheme": parsed.scheme or "http",
            "host": parsed.hostname or "",
            "port": parsed.port or 8080,
            "username": parsed.username,
            "password": parsed.password,
        }

# Global singleton
_proxy_wrapper: Optional[ProxyWrapper] = None

def get_proxy_wrapper() -> ProxyWrapper:
    global _proxy_wrapper
    if _proxy_wrapper is None:
        _proxy_wrapper = ProxyWrapper()
    return _proxy_wrapper
