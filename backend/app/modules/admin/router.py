import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.core.errors import BadRequestError, ForbiddenError, NotFoundError
from app.core.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    apply_keyset,
    build_page,
    decode_cursor,
    encode_cursor,
)
from app.db.session import DbSession
from app.modules.admin.schemas import (
    AdminStats,
    AdminUpdateUserRequest,
    AdminUserPage,
    AdminUserResponse,
)
from app.modules.auth.dependencies import AdminUser
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.comments.models import Comment
from app.modules.posts.models import Post
from app.modules.reactions.models import Reaction
from app.modules.users.models import User
from app.modules.users.service import invalidate_profile_cache

# Every route here depends on AdminUser: role is checked on the server for each request.
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserPage)
async def list_users(
    _: AdminUser,
    session: DbSession,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    is_active: bool | None = None,
) -> AdminUserPage:
    stmt = select(User)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    stmt = apply_keyset(stmt, User.created_at, User.id, decode_cursor(cursor))
    stmt = stmt.order_by(User.created_at.desc(), User.id.desc()).limit(limit + 1)
    rows = list((await session.execute(stmt)).scalars().all())
    items, next_cursor = build_page(rows, limit, lambda u: encode_cursor(u.created_at, u.id))
    return AdminUserPage(
        items=[AdminUserResponse.model_validate(u) for u in items], next_cursor=next_cursor
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUpdateUserRequest,
    admin: AdminUser,
    session: DbSession,
) -> AdminUserResponse:
    if user_id == admin.id:
        raise ForbiddenError("Admins cannot change their own role or status", code="SELF_MODIFY")
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found", code="USER_NOT_FOUND")
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise BadRequestError("Fields cannot be null", code="VALIDATION_ERROR")
    if "role" in changes:
        user.role = changes["role"].value
    if "is_active" in changes:
        user.is_active = changes["is_active"]
        if not user.is_active:  # banning also logs the user out everywhere
            await RefreshTokenRepository(session).revoke_all_for_user(user.id, datetime.now(UTC))
    await session.commit()
    await invalidate_profile_cache(user.username)
    return AdminUserResponse.model_validate(user)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_any_post(post_id: uuid.UUID, _: AdminUser, session: DbSession) -> None:
    post = await session.get(Post, post_id)
    if post is None:
        raise NotFoundError("Post not found", code="POST_NOT_FOUND")
    await session.delete(post)
    await session.commit()


@router.get("/stats", response_model=AdminStats)
async def read_stats(_: AdminUser, session: DbSession) -> AdminStats:
    async def count(statement):  # type: ignore[no-untyped-def]
        return int((await session.execute(statement)).scalar_one())

    return AdminStats(
        users=await count(select(func.count()).select_from(User)),
        active_users=await count(
            select(func.count()).select_from(User).where(User.is_active.is_(True))
        ),
        posts=await count(select(func.count()).select_from(Post)),
        comments=await count(select(func.count()).select_from(Comment)),
        reactions=await count(select(func.count()).select_from(Reaction)),
    )
