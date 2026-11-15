import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Cursor, apply_keyset
from app.modules.posts.models import Post
from app.modules.users.models import Follow, User


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _visible(stmt: Select) -> Select:  # type: ignore[type-arg]
    """Hide banned and self-deactivated accounts from public queries."""
    return stmt.where(User.is_active.is_(True), User.deactivated_at.is_(None))


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_google_sub(self, google_sub: str) -> User | None:
        result = await self._session.execute(select(User).where(User.google_sub == google_sub))
        return result.scalar_one_or_none()

    async def get_visible_by_username(self, username: str) -> User | None:
        stmt = _visible(select(User).where(User.username == username.lower()))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_or_username_exists(self, email: str, username: str) -> bool:
        stmt = select(User.id).where(or_(User.email == email, User.username == username)).limit(1)
        return (await self._session.execute(stmt)).first() is not None

    async def username_exists(self, username: str) -> bool:
        stmt = select(User.id).where(User.username == username).limit(1)
        return (await self._session.execute(stmt)).first() is not None

    async def add(self, user: User) -> None:
        self._session.add(user)
        await self._session.flush()

    async def delete(self, user: User) -> None:
        await self._session.delete(user)

    async def search(self, query: str, limit: int) -> Sequence[User]:
        pattern = _escape_like(query.lower()) + "%"
        stmt = _visible(
            select(User).where(
                or_(
                    User.username.like(pattern, escape="\\"),
                    func.lower(User.display_name).like(pattern, escape="\\"),
                )
            )
        )
        stmt = stmt.order_by(User.username).limit(limit)
        return (await self._session.execute(stmt)).scalars().all()

    # --- counters (used by the profile endpoint) ---------------------------------
    async def count_followers(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Follow).where(Follow.followee_id == user_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_following(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Follow).where(Follow.follower_id == user_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_posts(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Post).where(Post.author_id == user_id)
        return int((await self._session.execute(stmt)).scalar_one())

    # --- follows ---------------------------------------------------------------------
    async def is_following(self, follower_id: uuid.UUID, followee_id: uuid.UUID) -> bool:
        stmt = (
            select(Follow.follower_id)
            .where(Follow.follower_id == follower_id, Follow.followee_id == followee_id)
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def add_follow(self, follower_id: uuid.UUID, followee_id: uuid.UUID) -> None:
        stmt = (
            insert(Follow)
            .values(follower_id=follower_id, followee_id=followee_id)
            .on_conflict_do_nothing()
        )
        await self._session.execute(stmt)

    async def remove_follow(self, follower_id: uuid.UUID, followee_id: uuid.UUID) -> None:
        stmt = delete(Follow).where(
            Follow.follower_id == follower_id, Follow.followee_id == followee_id
        )
        await self._session.execute(stmt)

    async def list_followers(
        self, user_id: uuid.UUID, cursor: Cursor | None, limit: int
    ) -> Sequence[tuple[User, datetime]]:
        stmt = _visible(
            select(User, Follow.created_at)
            .join(Follow, Follow.follower_id == User.id)
            .where(Follow.followee_id == user_id)
        )
        stmt = apply_keyset(stmt, Follow.created_at, User.id, cursor)
        stmt = stmt.order_by(Follow.created_at.desc(), User.id.desc()).limit(limit + 1)
        return [(row[0], row[1]) for row in (await self._session.execute(stmt)).all()]

    async def list_following(
        self, user_id: uuid.UUID, cursor: Cursor | None, limit: int
    ) -> Sequence[tuple[User, datetime]]:
        stmt = _visible(
            select(User, Follow.created_at)
            .join(Follow, Follow.followee_id == User.id)
            .where(Follow.follower_id == user_id)
        )
        stmt = apply_keyset(stmt, Follow.created_at, User.id, cursor)
        stmt = stmt.order_by(Follow.created_at.desc(), User.id.desc()).limit(limit + 1)
        return [(row[0], row[1]) for row in (await self._session.execute(stmt)).all()]
