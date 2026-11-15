import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Select, delete, func, null, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, joinedload

from app.core.pagination import Cursor, apply_keyset
from app.modules.comments.models import Comment
from app.modules.posts.models import Post
from app.modules.reactions.models import Reaction
from app.modules.users.models import Follow, User


@dataclass(frozen=True)
class PostRow:
    post: Post
    reaction_count: int
    comment_count: int
    my_reaction: str | None


def post_select(viewer_id: uuid.UUID | None) -> Select:  # type: ignore[type-arg]
    """The one query every post list/detail is built from.

    Counts are correlated subqueries (index-backed), so there is no N+1 and no
    cartesian product. Posts of banned/deactivated authors are hidden.
    """
    reaction_count = (
        select(func.count())
        .select_from(Reaction)
        .where(Reaction.post_id == Post.id)
        .correlate(Post)
        .scalar_subquery()
    )
    comment_count = (
        select(func.count())
        .select_from(Comment)
        .where(Comment.post_id == Post.id)
        .correlate(Post)
        .scalar_subquery()
    )
    if viewer_id is None:
        my_reaction = null()
    else:
        my_reaction = (
            select(Reaction.type)
            .where(Reaction.post_id == Post.id, Reaction.user_id == viewer_id)
            .correlate(Post)
            .scalar_subquery()
        )
    return (
        select(
            Post,
            reaction_count.label("reaction_count"),
            comment_count.label("comment_count"),
            my_reaction.label("my_reaction"),
        )
        .join(User, User.id == Post.author_id)
        .where(User.is_active.is_(True), User.deactivated_at.is_(None))
        .options(contains_eager(Post.author), joinedload(Post.media))
        # Re-populate relations even if the Post is already in the session's identity map
        # (e.g. right after creating it), because relations are lazy="raise".
        .execution_options(populate_existing=True)
    )


def _to_rows(raw: Sequence) -> list[PostRow]:  # type: ignore[type-arg]
    return [
        PostRow(post=r[0], reaction_count=int(r[1]), comment_count=int(r[2]), my_reaction=r[3])
        for r in raw
    ]


class PostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, post: Post) -> None:
        self._session.add(post)

    async def get_row(self, post_id: uuid.UUID, viewer_id: uuid.UUID | None) -> PostRow | None:
        stmt = post_select(viewer_id).where(Post.id == post_id)
        rows = _to_rows((await self._session.execute(stmt)).all())
        return rows[0] if rows else None

    async def get_raw(self, post_id: uuid.UUID) -> Post | None:
        """Plain post without relations (for ownership checks and deletes)."""
        return await self._session.get(Post, post_id)

    async def delete(self, post: Post) -> None:
        await self._session.execute(delete(Post).where(Post.id == post.id))

    async def list_rows(
        self,
        *,
        viewer_id: uuid.UUID | None,
        cursor: Cursor | None,
        limit: int,
        author_id: uuid.UUID | None = None,
        feed_of: uuid.UUID | None = None,
        has_image: bool | None = None,
    ) -> list[PostRow]:
        stmt = post_select(viewer_id)
        if author_id is not None:
            stmt = stmt.where(Post.author_id == author_id)
        if feed_of is not None:
            followed = select(Follow.followee_id).where(Follow.follower_id == feed_of)
            stmt = stmt.where((Post.author_id == feed_of) | Post.author_id.in_(followed))
        if has_image is True:
            stmt = stmt.where(Post.media_id.is_not(None))
        elif has_image is False:
            stmt = stmt.where(Post.media_id.is_(None))
        stmt = apply_keyset(stmt, Post.created_at, Post.id, cursor)
        stmt = stmt.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit + 1)
        return _to_rows((await self._session.execute(stmt)).all())
