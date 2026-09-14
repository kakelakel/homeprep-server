from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _same_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        referer = request.headers.get("referer")
        if not referer:
            return False
        parsed = urlsplit(referer)
        origin = f"{parsed.scheme}://{parsed.netloc}"
    parsed_origin = urlsplit(origin)
    request_host = request.headers.get("host", "")
    return parsed_origin.netloc.casefold() == request_host.casefold()


class WebSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        has_web_session = bool(request.cookies.get("homeprep_session"))
        bearer = request.headers.get("authorization", "").casefold().startswith("bearer ")
        if (
            request.url.path.startswith("/api/")
            and request.method.upper() in UNSAFE_METHODS
            and has_web_session
            and not bearer
            and not _same_origin(request)
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "cross_site_request_blocked",
                        "message": "Cross-site state-changing requests are not allowed",
                        "details": None,
                    }
                },
            )

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "connect-src 'self'"
        )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.url.path.startswith("/api/v1/auth"):
            response.headers["Cache-Control"] = "no-store"
        return response
