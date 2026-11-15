from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.rate_limit import RateLimit
from app.db.session import DbSession
from app.modules.auth.dependencies import CurrentUser, OptionalUser
from app.modules.posts.schemas import PostPage
from app.modules.posts.service import PostService
from app.modules.users.schemas import (
    PublicProfile,
    UpdateProfileRequest,
    UserMeResponse,
    UserPage,
    UserSummary,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])

Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
CursorParam = Annotated[str | None, Query(max_length=200)]


@router.get("/me", response_model=UserMeResponse)
async def read_current_user(current_user: CurrentUser) -> UserMeResponse:
    return UserMeResponse.model_validate(current_user)


@router.patch("/me", response_model=UserMeResponse)
async def update_current_user(
    payload: UpdateProfileRequest, current_user: CurrentUser, session: DbSession
) -> UserMeResponse:
    user = await UserService(session).update_profile(current_user, payload)
    return UserMeResponse.model_validate(user)


@router.post(
    "/me/avatar",
    response_model=UserMeResponse,
    dependencies=[Depends(RateLimit("avatar", 20, 3600, per="user"))],
)
async def upload_avatar(
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP, max 5 MB")],
    current_user: CurrentUser,
    session: DbSession,
) -> UserMeResponse:
    user = await UserService(session).set_avatar(current_user, file)
    return UserMeResponse.model_validate(user)


@router.get("/search", response_model=list[UserSummary])
async def search_users(
    session: DbSession,
    q: Annotated[str, Query(min_length=2, max_length=50)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> list[UserSummary]:
    return await UserService(session).search(q, limit)


@router.get("/{username}", response_model=PublicProfile)
async def read_profile(
    username: str, viewer: OptionalUser, session: DbSession
) -> PublicProfile:
    return await UserService(session).get_profile(username, viewer)


@router.get("/{username}/posts", response_model=PostPage)
async def read_user_posts(
    username: str,
    viewer: OptionalUser,
    session: DbSession,
    cursor: CursorParam = None,
    limit: Limit = DEFAULT_PAGE_SIZE,
    has_image: bool | None = None,
) -> PostPage:
    return await PostService(session).list_by_user(
        username, viewer, cursor=cursor, limit=limit, has_image=has_image
    )


@router.post(
    "/{username}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RateLimit("follow", 60, 3600, per="user"))],
)
async def follow_user(username: str, current_user: CurrentUser, session: DbSession) -> None:
    await UserService(session).follow(current_user, username)


@router.delete("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(username: str, current_user: CurrentUser, session: DbSession) -> None:
    await UserService(session).unfollow(current_user, username)


@router.get("/{username}/followers", response_model=UserPage)
async def read_followers(
    username: str,
    session: DbSession,
    cursor: CursorParam = None,
    limit: Limit = DEFAULT_PAGE_SIZE,
) -> UserPage:
    return await UserService(session).followers(username, cursor, limit)


@router.get("/{username}/following", response_model=UserPage)
async def read_following(
    username: str,
    session: DbSession,
    cursor: CursorParam = None,
    limit: Limit = DEFAULT_PAGE_SIZE,
) -> UserPage:
    return await UserService(session).following(username, cursor, limit)
