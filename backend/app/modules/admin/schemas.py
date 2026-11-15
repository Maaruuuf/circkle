import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.users.models import UserRole


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    is_email_verified: bool
    deactivated_at: datetime | None
    last_login_at: datetime | None
    created_at: datetime


class AdminUserPage(BaseModel):
    items: list[AdminUserResponse]
    next_cursor: str | None


class AdminUpdateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool | None = None
    role: UserRole | None = None


class AdminStats(BaseModel):
    users: int
    active_users: int
    posts: int
    comments: int
    reactions: int
