import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.posts.models import Post
from app.modules.reactions.models import Reaction
from app.modules.reactions.schemas import ReactionSummary
from app.modules.users.models import User


class ReactionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _ensure_post(self, post_id: uuid.UUID) -> None:
        if await self._session.get(Post, post_id) is None:
            raise NotFoundError("Post not found", code="POST_NOT_FOUND")

    async def set_reaction(
        self, post_id: uuid.UUID, user: User, reaction_type: str
    ) -> ReactionSummary:
        await self._ensure_post(post_id)
        # One atomic statement: insert, or switch the type if the user already reacted.
        stmt = (
            insert(Reaction)
            .values(post_id=post_id, user_id=user.id, type=reaction_type)
            .on_conflict_do_update(
                index_elements=[Reaction.post_id, Reaction.user_id],
                set_={"type": reaction_type},
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return await self.summary(post_id, user)

    async def remove_reaction(self, post_id: uuid.UUID, user: User) -> ReactionSummary:
        await self._ensure_post(post_id)
        await self._session.execute(
            delete(Reaction).where(Reaction.post_id == post_id, Reaction.user_id == user.id)
        )
        await self._session.commit()
        return await self.summary(post_id, user)

    async def summary(self, post_id: uuid.UUID, viewer: User | None) -> ReactionSummary:
        await self._ensure_post(post_id)
        rows = (
            await self._session.execute(
                select(Reaction.type, func.count())
                .where(Reaction.post_id == post_id)
                .group_by(Reaction.type)
            )
        ).all()
        by_type = {row[0]: int(row[1]) for row in rows}
        mine: str | None = None
        if viewer is not None:
            mine = (
                await self._session.execute(
                    select(Reaction.type).where(
                        Reaction.post_id == post_id, Reaction.user_id == viewer.id
                    )
                )
            ).scalar_one_or_none()
        return ReactionSummary(
            post_id=post_id,
            reaction_count=sum(by_type.values()),
            my_reaction=mine,
            by_type=by_type,
        )
