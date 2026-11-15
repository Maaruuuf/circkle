import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.rate_limit import RateLimit
from app.core.webhooks import dispatch_event
from app.db.session import DbSession
from app.modules.auth.dependencies import CurrentUser, OptionalUser
from app.modules.comments.router import router as comments_router
from app.modules.posts.schemas import CreatePostRequest, PostPage, PostResponse, UpdatePostRequest
from app.modules.posts.service import PostService
from app.modules.reactions.router import router as reactions_router

router = APIRouter(prefix="/posts", tags=["posts"])

Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
CursorParam = Annotated[str | None, Query(max_length=200)]


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit("create_post", 30, 3600, per="user"))],
)
async def create_post(
    payload: CreatePostRequest,
    current_user: CurrentUser,
    session: DbSession,
    background_tasks: BackgroundTasks,
) -> PostResponse:
    post = await PostService(session).create(current_user, payload)
    background_tasks.add_task(
        dispatch_event, "post.created", {"id": str(post.id), "author": current_user.username}
    )
    return post


# Static paths first so "/feed" is never read as a post id.
@router.get("/feed", response_model=PostPage)
async def read_feed(
    current_user: CurrentUser,
    session: DbSession,
    cursor: CursorParam = None,
    limit: Limit = DEFAULT_PAGE_SIZE,
) -> PostPage:
    """Posts from people you follow, plus your own, newest first."""
    return await PostService(session).feed(current_user, cursor, limit)


@router.get("/explore", response_model=PostPage)
async def read_explore(
    viewer: OptionalUser,
    session: DbSession,
    cursor: CursorParam = None,
    limit: Limit = DEFAULT_PAGE_SIZE,
    has_image: bool | None = None,
) -> PostPage:
    """Newest posts from everyone. `has_image=true|false` filters by media."""
    return await PostService(session).explore(viewer, cursor, limit, has_image)


@router.get("/{post_id}", response_model=PostResponse)
async def read_post(post_id: uuid.UUID, viewer: OptionalUser, session: DbSession) -> PostResponse:
    return await PostService(session).get(post_id, viewer)


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: uuid.UUID, payload: UpdatePostRequest, current_user: CurrentUser, session: DbSession
) -> PostResponse:
    return await PostService(session).update(post_id, current_user, payload)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: uuid.UUID, current_user: CurrentUser, session: DbSession) -> None:
    await PostService(session).delete(post_id, current_user)


router.include_router(reactions_router)
router.include_router(comments_router)
