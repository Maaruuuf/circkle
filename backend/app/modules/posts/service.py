import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, ForbiddenError, NotFoundError
from app.core.pagination import build_page, decode_cursor, encode_cursor
from app.modules.media.models import Media
from app.modules.media.storage import media_url
from app.modules.posts.models import Post
from app.modules.posts.repository import PostRepository, PostRow
from app.modules.posts.schemas import (
    CreatePostRequest,
    PostPage,
    PostResponse,
    UpdatePostRequest,
)
from app.modules.users.models import User, UserRole
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserSummary
from app.modules.users.service import invalidate_profile_cache


def to_response(row: PostRow) -> PostResponse:
    post = row.post
    return PostResponse(
        id=post.id,
        content=post.content,
        image_url=media_url(post.media.key) if post.media else None,
        created_at=post.created_at,
        updated_at=post.updated_at,
        author=UserSummary.model_validate(post.author),
        reaction_count=row.reaction_count,
        comment_count=row.comment_count,
        my_reaction=row.my_reaction,
    )


class PostService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._posts = PostRepository(session)
        self._users = UserRepository(session)

    def _page(self, rows: list[PostRow], limit: int) -> PostPage:
        items, next_cursor = build_page(
            rows, limit, lambda r: encode_cursor(r.post.created_at, r.post.id)
        )
        return PostPage(items=[to_response(r) for r in items], next_cursor=next_cursor)

    async def create(self, author: User, data: CreatePostRequest) -> PostResponse:
        if data.content is None and data.media_id is None:
            raise BadRequestError("A post needs text or an image", code="EMPTY_POST")
        if data.media_id is not None:
            media = await self._session.get(Media, data.media_id)
            # Only your own uploads: otherwise anyone could attach someone else's image.
            if media is None or media.owner_id != author.id:
                raise BadRequestError("Unknown image", code="INVALID_MEDIA")

        post = Post(id=uuid.uuid4(), author_id=author.id, content=data.content, media_id=data.media_id)
        self._posts.add(post)
        await self._session.commit()
        await invalidate_profile_cache(author.username)
        return await self.get(post.id, author)

    async def get(self, post_id: uuid.UUID, viewer: User | None) -> PostResponse:
        row = await self._posts.get_row(post_id, viewer.id if viewer else None)
        if row is None:
            raise NotFoundError("Post not found", code="POST_NOT_FOUND")
        return to_response(row)

    async def update(
        self, post_id: uuid.UUID, user: User, data: UpdatePostRequest
    ) -> PostResponse:
        post = await self._posts.get_raw(post_id)
        if post is None:
            raise NotFoundError("Post not found", code="POST_NOT_FOUND")
        if post.author_id != user.id:  # even admins edit nobody's words
            raise ForbiddenError()
        post.content = data.content
        await self._session.commit()
        return await self.get(post_id, user)

    async def delete(self, post_id: uuid.UUID, user: User) -> None:
        post = await self._posts.get_raw(post_id)
        if post is None:
            raise NotFoundError("Post not found", code="POST_NOT_FOUND")
        if post.author_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenError()
        author = await self._users.get_by_id(post.author_id)
        await self._posts.delete(post)
        await self._session.commit()
        if author is not None:
            await invalidate_profile_cache(author.username)

    async def feed(self, user: User, cursor: str | None, limit: int) -> PostPage:
        rows = await self._posts.list_rows(
            viewer_id=user.id, feed_of=user.id, cursor=decode_cursor(cursor), limit=limit
        )
        return self._page(rows, limit)

    async def explore(
        self, viewer: User | None, cursor: str | None, limit: int, has_image: bool | None
    ) -> PostPage:
        rows = await self._posts.list_rows(
            viewer_id=viewer.id if viewer else None,
            cursor=decode_cursor(cursor),
            limit=limit,
            has_image=has_image,
        )
        return self._page(rows, limit)

    async def list_by_user(
        self,
        username: str,
        viewer: User | None,
        *,
        cursor: str | None,
        limit: int,
        has_image: bool | None,
    ) -> PostPage:
        author = await self._users.get_visible_by_username(username)
        if author is None:
            raise NotFoundError("User not found", code="USER_NOT_FOUND")
        rows = await self._posts.list_rows(
            viewer_id=viewer.id if viewer else None,
            author_id=author.id,
            cursor=decode_cursor(cursor),
            limit=limit,
            has_image=has_image,
        )
        return self._page(rows, limit)
