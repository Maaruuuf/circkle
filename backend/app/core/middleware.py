import logging
import re
import time
import uuid

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings
from app.core.request_context import request_id_var

logger = logging.getLogger("app.request")

_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Request id + structured access log + security headers on every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            request_id_var.reset(token)
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        response.headers["X-Request-ID"] = request_id
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        if get_settings().environment == "production":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        logger.info(
            "request",
            extra={
                "fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                }
            },
        )
        request_id_var.reset(token)
        return response


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """CSRF defence in depth (on top of SameSite cookies).

    Browsers always attach an Origin header to cross-site POST/PUT/PATCH/DELETE.
    If it is present and is not one of our own origins, the request is rejected.
    Requests without Origin (curl, server-to-server, tests) are not browsers
    under an attacker's control, so they pass.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("origin")
        if request.method in UNSAFE_METHODS and origin is not None:
            origin_host = origin.split("://", 1)[-1]
            same_origin = origin_host == request.headers.get("host")
            if not same_origin and origin.rstrip("/") not in get_settings().allowed_origins:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "CSRF_ORIGIN_REJECTED",
                            "message": "Cross-site request rejected",
                            "request_id": getattr(request.state, "request_id", "-"),
                        }
                    },
                )
        return await call_next(request)
