import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.core.errors import ForbiddenError, NotFoundError
from app.core.pagination import apply_keyset, build_page, decode_cursor, encode_cursor
from app.modules.comments.models import Comment
from app.modules.comments.schemas import CommentOrder, CommentPage, CommentResponse
from app.modules.posts.models import Post
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserSummary


def _to_response(comment: Comment) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        content=comment.content,
        created_at=comment.created_at,
        author=UserSummary.model_validate(comment.author),
    )


class CommentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _post_exists(self, post_id: uuid.UUID) -> Post:
        post = await self._session.get(Post, post_id)
        if post is None:
            raise NotFoundError("Post not found", code="POST_NOT_FOUND")
        return post

    def _select(self):  # type: ignore[no-untyped-def]
        return (
            select(Comment)
            .join(User, User.id == Comment.author_id)
            .where(User.is_active.is_(True), User.deactivated_at.is_(None))
            .options(contains_eager(Comment.author))
            .execution_options(populate_existing=True)
        )

    async def create(self, post_id: uuid.UUID, author: User, content: str) -> CommentResponse:
        await self._post_exists(post_id)
        comment = Comment(id=uuid.uuid4(), post_id=post_id, author_id=author.id, content=content)
        self._session.add(comment)
        await self._session.commit()
        stmt = self._select().where(Comment.id == comment.id)
        created = (await self._session.execute(stmt)).scalar_one()
        return _to_response(created)

    async def list_for_post(
        self, post_id: uuid.UUID, cursor: str | None, limit: int, order: CommentOrder
    ) -> CommentPage:
        await self._post_exists(post_id)
        descending = order == "desc"
        stmt = self._select().where(Comment.post_id == post_id)
        stmt = apply_keyset(
            stmt, Comment.created_at, Comment.id, decode_cursor(cursor), descending=descending
        )
        ordering = (
            (Comment.created_at.desc(), Comment.id.desc())
            if descending
            else (Comment.created_at.asc(), Comment.id.asc())
        )
        stmt = stmt.order_by(*ordering).limit(limit + 1)
        rows = list((await self._session.execute(stmt)).scalars().all())
        items, next_cursor = build_page(rows, limit, lambda c: encode_cursor(c.created_at, c.id))
        return CommentPage(items=[_to_response(c) for c in items], next_cursor=next_cursor)

    async def delete(self, comment_id: uuid.UUID, user: User) -> None:
        comment = await self._session.get(Comment, comment_id)
        if comment is None:
            raise NotFoundError("Comment not found", code="COMMENT_NOT_FOUND")
        post = await self._session.get(Post, comment.post_id)
        allowed = (
            comment.author_id == user.id  # your own comment
            or (post is not None and post.author_id == user.id)  # comment on your post
            or user.role == UserRole.ADMIN
        )
        if not allowed:
            raise ForbiddenError()
        await self._session.delete(comment)
        await self._session.commit()
