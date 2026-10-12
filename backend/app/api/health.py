from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Is the process alive? Never touches the database."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """Can this instance serve traffic? Checks the database."""
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Do not leak internal error details to the client.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from None
    return {"status": "ready"}