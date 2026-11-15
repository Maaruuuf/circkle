import uuid
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete, cache_get_json, cache_set_json
from app.core.errors import BadRequestError, NotFoundError
from app.core.pagination import build_page, decode_cursor, encode_cursor
from app.modules.media.images import AVATAR_SIZE
from app.modules.media.service import MediaService
from app.modules.media.storage import media_url
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import PublicProfile, UpdateProfileRequest, UserPage, UserSummary

PROFILE_CACHE_TTL_SECONDS = 60


def profile_cache_key(username: str) -> str:
    return f"profile:{username}"


async def invalidate_profile_cache(*usernames: str) -> None:
    await cache_delete(*(profile_cache_key(name) for name in usernames))


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)

    async def _get_visible_or_404(self, username: str) -> User:
        user = await self._users.get_visible_by_username(username)
        if user is None:
            raise NotFoundError("User not found", code="USER_NOT_FOUND")
        return user

    async def get_profile(self, username: str, viewer: User | None) -> PublicProfile:
        """Cache-aside: the viewer-independent part is cached, `is_following` is not."""
        key = profile_cache_key(username.lower())
        data: dict[str, Any] | None = await cache_get_json(key)
        if data is None:
            user = await self._get_visible_or_404(username)
            data = {
                "id": str(user.id),
                "username": user.username,
                "display_name": user.display_name,
                "bio": user.bio,
                "avatar_url": user.avatar_url,
                "created_at": user.created_at.isoformat(),
                "followers_count": await self._users.count_followers(user.id),
                "following_count": await self._users.count_following(user.id),
                "posts_count": await self._users.count_posts(user.id),
            }
            await cache_set_json(key, data, PROFILE_CACHE_TTL_SECONDS)

        profile_id = uuid.UUID(data["id"])
        is_me = viewer is not None and viewer.id == profile_id
        is_following = (
            viewer is not None
            and not is_me
            and await self._users.is_following(viewer.id, profile_id)
        )
        return PublicProfile(**data, is_following=is_following, is_me=is_me)

    async def update_profile(self, user: User, data: UpdateProfileRequest) -> User:
        changes = data.model_dump(exclude_unset=True)
        if "display_name" in changes and changes["display_name"] is None:
            raise BadRequestError("display_name cannot be null", code="VALIDATION_ERROR")
        if "display_name" in changes:
            user.display_name = changes["display_name"]
        if "bio" in changes:
            user.bio = changes["bio"] or None  # empty string clears the bio
        await self._session.commit()
        await invalidate_profile_cache(user.username)
        return user

    async def set_avatar(self, user: User, file: UploadFile) -> User:
        media = await MediaService(self._session).upload_image(
            user.id, file, square=AVATAR_SIZE
        )
        user.avatar_url = media_url(media.key)
        await self._session.commit()
        await invalidate_profile_cache(user.username)
        return user

    async def search(self, query: str, limit: int) -> list[UserSummary]:
        users = await self._users.search(query.strip(), limit)
        return [UserSummary.model_validate(user) for user in users]

    async def follow(self, follower: User, username: str) -> None:
        target = await self._get_visible_or_404(username)
        if target.id == follower.id:
            raise BadRequestError("You cannot follow yourself", code="CANNOT_FOLLOW_SELF")
        await self._users.add_follow(follower.id, target.id)  # idempotent
        await self._session.commit()
        await invalidate_profile_cache(follower.username, target.username)

    async def unfollow(self, follower: User, username: str) -> None:
        target = await self._get_visible_or_404(username)
        await self._users.remove_follow(follower.id, target.id)  # idempotent
        await self._session.commit()
        await invalidate_profile_cache(follower.username, target.username)

    async def followers(self, username: str, cursor: str | None, limit: int) -> UserPage:
        target = await self._get_visible_or_404(username)
        rows = await self._users.list_followers(target.id, decode_cursor(cursor), limit)
        page, next_cursor = build_page(rows, limit, lambda r: encode_cursor(r[1], r[0].id))
        return UserPage(items=[UserSummary.model_validate(r[0]) for r in page], next_cursor=next_cursor)

    async def following(self, username: str, cursor: str | None, limit: int) -> UserPage:
        target = await self._get_visible_or_404(username)
        rows = await self._users.list_following(target.id, decode_cursor(cursor), limit)
        page, next_cursor = build_page(rows, limit, lambda r: encode_cursor(r[1], r[0].id))
        return UserPage(items=[UserSummary.model_validate(r[0]) for r in page], next_cursor=next_cursor)
