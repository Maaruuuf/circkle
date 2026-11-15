import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import OriginCheckMiddleware, RequestContextMiddleware
from app.core.rate_limit import RateLimit
from app.core.redis import close_redis
from app.db import registry  # noqa: F401  (registers every model)
from app.db.session import engine
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.comments.router import item_router as comments_item_router
from app.modules.media.router import files_router as media_files_router
from app.modules.media.router import router as media_router
from app.modules.posts.router import router as posts_router
from app.modules.users.router import router as users_router

settings = get_settings()
configure_logging(settings.log_level, settings.log_json)
logger = logging.getLogger(__name__)
is_production = settings.environment == "production"

API_V1_PREFIX = "/api/v1"


def _init_sentry() -> None:
    if not settings.sentry_dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        send_default_pii=False,  # never send cookies / emails to the error tracker
        traces_sample_rate=0.0,
    )


_init_sentry()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("starting %s (%s)", settings.app_name, settings.environment)
    yield
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title=f"{settings.app_name} API",
    version="1.0.0",
    description="Circkle: a small Instagram-style social network.",
    debug=settings.debug,
    lifespan=lifespan,
    # Generous per-IP safety net on every route; stricter limits sit on sensitive routes.
    dependencies=[
        Depends(RateLimit("global", 300, 60, skip_prefixes=("/health", "/media/")))
    ],
    # Hide API docs in production.
    docs_url=None if is_production else "/docs",
    redoc_url=None,
    openapi_url=None if is_production else "/openapi.json",
)

register_exception_handlers(app)

# Middleware order: the LAST one added runs FIRST (outermost).
app.add_middleware(OriginCheckMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Retry-After"],
)

app.include_router(health_router)
app.include_router(media_files_router)
for api_router in (
    auth_router,
    users_router,
    posts_router,
    comments_item_router,
    media_router,
    admin_router,
):
    app.include_router(api_router, prefix=API_V1_PREFIX)
