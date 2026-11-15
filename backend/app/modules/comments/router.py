import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.rate_limit import RateLimit
from app.db.session import DbSession
from app.modules.auth.dependencies import CurrentUser
from app.modules.comments.schemas import (
    CommentOrder,
    CommentPage,
    CommentResponse,
    CreateCommentRequest,
)
from app.modules.comments.service import CommentService

# Mounted under /posts by the posts router: /posts/{post_id}/comments
router = APIRouter(tags=["comments"])
# Mounted at /comments: delete by comment id
item_router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("/{post_id}/comments", response_model=CommentPage)
async def list_comments(
    post_id: uuid.UUID,
    session: DbSession,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    order: CommentOrder = "asc",
) -> CommentPage:
    return await CommentService(session).list_for_post(post_id, cursor, limit, order)


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit("create_comment", 60, 3600, per="user"))],
)
async def create_comment(
    post_id: uuid.UUID,
    payload: CreateCommentRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> CommentResponse:
    return await CommentService(session).create(post_id, current_user, payload.content)


@item_router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID, current_user: CurrentUser, session: DbSession
) -> None:
    await CommentService(session).delete(comment_id, current_user)
