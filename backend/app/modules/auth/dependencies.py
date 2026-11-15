from typing import Annotated

from fastapi import Cookie, Depends

from app.core.errors import ForbiddenError, UnauthenticatedError
from app.core.security import decode_access_token
from app.db.session import DbSession
from app.modules.auth.service import AuthService
from app.modules.users.models import User, UserRole
from app.modules.users.repository import UserRepository


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(session)


async def get_optional_user(
    session: DbSession,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User | None:
    """The logged-in user, or None for guests / expired or invalid tokens."""
    if access_token is None:
        return None
    user_id = decode_access_token(access_token)
    if user_id is None:
        return None
    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active or user.deactivated_at is not None:
        return None
    return user


async def get_current_user(
    user: Annotated[User | None, Depends(get_optional_user)],
) -> User:
    if user is None:
        raise UnauthenticatedError()
    return user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError()
    return user


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
