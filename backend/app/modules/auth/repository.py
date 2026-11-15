import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AuthToken, RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, token: RefreshToken) -> None:
        self._session.add(token)

    async def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        """Row-locks the token so two parallel refreshes cannot both use it."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def revoke_family(self, family_id: uuid.UUID, revoked_at: datetime) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        await self._session.execute(stmt)

    async def revoke_all_for_user(self, user_id: uuid.UUID, revoked_at: datetime) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        await self._session.execute(stmt)


class AuthTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, token: AuthToken) -> None:
        self._session.add(token)

    async def get_by_hash_for_update(self, token_hash: str) -> AuthToken | None:
        stmt = select(AuthToken).where(AuthToken.token_hash == token_hash).with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def invalidate_unused(
        self, user_id: uuid.UUID, purpose: str, used_at: datetime
    ) -> None:
        """Mark older unused tokens as used, so only the newest emailed link works."""
        stmt = (
            update(AuthToken)
            .where(
                AuthToken.user_id == user_id,
                AuthToken.purpose == purpose,
                AuthToken.used_at.is_(None),
            )
            .values(used_at=used_at)
        )
        await self._session.execute(stmt)
