import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.redis import get_redis
from app.db.session import DbSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Is the process alive? Never touches the database. Used by Docker/orchestrators."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(session: DbSession) -> JSONResponse:
    """Can this instance serve traffic? Checks the database (required) and Redis (optional)."""
    checks: dict[str, str] = {}
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except SQLAlchemyError:
        logger.exception("readiness: database check failed")
        checks["database"] = "unavailable"

    redis = get_redis()
    if redis is None:
        checks["redis"] = "not_configured"
    else:
        try:
            await redis.ping()
            checks["redis"] = "ok"
        except RedisError:
            logger.warning("readiness: redis check failed")
            checks["redis"] = "unavailable"  # degraded, but the API still works

    ready = checks["database"] == "ok"
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "unavailable", "checks": checks},
    )
