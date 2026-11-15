"""One error format for the whole API.

Every error response looks like:
    {"error": {"code": "POST_NOT_FOUND", "message": "...", "details": [...], "request_id": "..."}}
Clients branch on `code`, never on `message`.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code: int = 400
    code: str = "BAD_REQUEST"
    message: str = "Bad request"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        headers: dict[str, str] | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.message
        if code is not None:
            self.code = code
        self.headers = headers
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400


class UnauthenticatedError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"
    message = "Not authenticated"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to do this"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "Conflict"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "FILE_TOO_LARGE"
    message = "File is too large"


class UnsupportedMediaError(AppError):
    status_code = 415
    code = "INVALID_IMAGE"
    message = "Unsupported or corrupt image"


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "Too many requests. Please slow down."

    def __init__(self, retry_after: int) -> None:
        super().__init__(headers={"Retry-After": str(retry_after)})


def error_body(
    code: str, message: str, request: Request, details: Any = None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", "-"),
    }
    if details is not None:
        body["details"] = details
    return {"error": body}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, request, exc.details),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Only field + message: never echo the submitted value (could be a password).
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"] if part != "body"),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_body("VALIDATION_ERROR", "Request validation failed", request, details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                codes.get(exc.status_code, "HTTP_ERROR"), str(exc.detail), request
            ),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_ERROR", "Something went wrong on our side", request),
        )
