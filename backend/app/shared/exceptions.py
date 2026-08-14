import logging

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import request_id_ctx

logger = logging.getLogger("app.errors")


class AppError(Exception):
    code = "APP_ERROR"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class ValidationAppError(AppError):
    code = "VALIDATION_ERROR"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


class AuthenticationError(AppError):
    code = "AUTHENTICATION_ERROR"
    status_code = status.HTTP_401_UNAUTHORIZED


class AuthorizationError(AppError):
    code = "AUTHORIZATION_ERROR"
    status_code = status.HTTP_403_FORBIDDEN


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT


class RateLimitError(AppError):
    code = "RATE_LIMITED"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


class UpstreamProviderError(AppError):
    code = "UPSTREAM_PROVIDER_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = request_id_ctx.get()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
            }
        },
    )


async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Reformats FastAPI's default {"detail": [...]} shape into the app's
    standard error envelope, so every error response — ours or the
    framework's — has the same shape (spec: "use consistent error responses")."""
    request_id = request_id_ctx.get()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": jsonable_encoder(exc.errors()),
                "request_id": request_id,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler: never leak a stack trace or internal exception
    message to the client (spec: "Never return stack traces to production
    clients"). The real error is logged server-side with its traceback."""
    request_id = request_id_ctx.get()
    logger.exception("Unhandled exception (request_id=%s)", request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
                "request_id": request_id,
            }
        },
    )
