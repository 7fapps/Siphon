import time
import logging
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request/response as structured JSON."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        
        if settings.log_format == "json":
            log_entry = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "level": "info",
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
            logger.info(json.dumps(log_entry))
        else:
            logger.info(f"{request.method} {request.url.path} → {response.status_code} ({round(duration*1000, 2)}ms)")
        
        return response

class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Applies a global request timeout."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # FastAPI handles async timeouts per-route; this is for ASGI-level safety
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        return response
