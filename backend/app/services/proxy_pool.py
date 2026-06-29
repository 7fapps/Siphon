from typing import List, Optional, Dict, Any, Iterator
import random
from app.config import get_settings

class ProxyPool:
    """
    Rotatable proxy pool supporting round-robin and random strategies.
    """
    
    def __init__(self):
        self._settings = get_settings()
        self._proxies: List[str] = []
        self._iter: Iterator[str] = iter([])
        self._load_proxies()
    
    def _load_proxies(self):
        urls = []
        if self._settings.proxy_url:
            urls.append(self._settings.proxy_url)
        if self._settings.proxy_urls:
            urls.extend([u.strip() for u in self._settings.proxy_urls.split(",") if u.strip()])
        self._proxies = urls
        self._reset_iter()
    
    def _reset_iter(self):
        if self._settings.proxy_rotation_strategy == "round_robin":
            self._iter = iter(self._proxies)
        else:
            random.shuffle(self._proxies)
            self._iter = iter(self._proxies)
    
    @property
    def has_proxies(self) -> bool:
        return len(self._proxies) > 0
    
    @property
    def count(self) -> int:
        return len(self._proxies)
    
    def get_next(self) -> Optional[str]:
        if not self._proxies:
            return None
        try:
            return next(self._iter)
        except StopIteration:
            self._reset_iter()
            return next(self._iter, None)
    
    def get_random(self) -> Optional[str]:
        if not self._proxies:
            return None
        return random.choice(self._proxies)
    
    def yt_dlp_args(self) -> List[str]:
        proxy = self.get_next() if self._settings.proxy_rotation_strategy == "round_robin" else self.get_random()
        if not proxy:
            return []
        return ["--proxy", proxy]
    
    def playwright_proxy(self) -> Optional[Dict[str, Any]]:
        proxy = self.get_next() if self._settings.proxy_rotation_strategy == "round_robin" else self.get_random()
        if not proxy:
            return None
        from urllib.parse import urlparse
        parsed = urlparse(proxy)
        cfg = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
        if parsed.username:
            cfg["username"] = parsed.username
        if parsed.password:
            cfg["password"] = parsed.password
        return cfg

# Global singleton
_pool: Optional[ProxyPool] = None

def get_proxy_pool() -> ProxyPool:
    global _pool
    if _pool is None:
        _pool = ProxyPool()
    return _pool
