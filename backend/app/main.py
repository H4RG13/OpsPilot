import uuid

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging, request_id_ctx
from app.modules.ai.conversations_router import router as ai_conversations_router
from app.modules.ai.usage_router import router as ai_usage_router
from app.modules.analytics.router import router as analytics_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import me_router
from app.modules.auth.router import router as auth_router
from app.modules.customers.router import router as customers_router
from app.modules.imports.router import router as imports_router
from app.modules.orders.router import router as orders_router
from app.modules.organizations.router import router as organizations_router
from app.modules.products.router import router as products_router
from app.modules.reports.router import router as reports_router
from app.modules.tasks.router import router as tasks_router
from app.shared.exceptions import (
    AppError,
    app_error_handler,
    request_validation_error_handler,
    unhandled_exception_handler,
)

configure_logging()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

API_V1_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(me_router, prefix=API_V1_PREFIX)
app.include_router(organizations_router, prefix=API_V1_PREFIX)
app.include_router(customers_router, prefix=API_V1_PREFIX)
app.include_router(products_router, prefix=API_V1_PREFIX)
app.include_router(orders_router, prefix=API_V1_PREFIX)
app.include_router(analytics_router, prefix=API_V1_PREFIX)
app.include_router(ai_usage_router, prefix=API_V1_PREFIX)
app.include_router(ai_conversations_router, prefix=API_V1_PREFIX)
app.include_router(tasks_router, prefix=API_V1_PREFIX)
app.include_router(reports_router, prefix=API_V1_PREFIX)
app.include_router(imports_router, prefix=API_V1_PREFIX)
app.include_router(audit_router, prefix=API_V1_PREFIX)


class ObservabilityMiddleware:
    """Plain ASGI middleware, not Starlette's BaseHTTPMiddleware (the
    `@app.middleware("http")` decorator) — that wrapper runs the downstream
    app inside its own anyio TaskGroup, which unreliably propagates
    exceptions to an app-level `Exception` handler (they surface as an
    ExceptionGroup instead), breaking the "never leak a stack trace" /
    consistent-error-envelope guarantee for genuinely unhandled errors.
    A raw ASGI middleware doesn't have that problem."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        request_id = headers.get(b"x-request-id", b"").decode() or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-request-id", request_id.encode()))
                response_headers.append((b"x-content-type-options", b"nosniff"))
                response_headers.append((b"x-frame-options", b"DENY"))
                response_headers.append(
                    (b"referrer-policy", b"strict-origin-when-cross-origin")
                )
                if settings.is_production:
                    response_headers.append(
                        (
                            b"strict-transport-security",
                            b"max-age=63072000; includeSubDomains",
                        )
                    )
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_ctx.reset(token)


app.add_middleware(ObservabilityMiddleware)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
