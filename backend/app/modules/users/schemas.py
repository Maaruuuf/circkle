import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.users.models import UserRole


class UserMeResponse(BaseModel):
    """The logged-in user's own data. Never include password_hash here."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    display_name: str
    bio: str | None
    avatar_url: str | None
    role: UserRole
    is_email_verified: bool
    has_password: bool
    created_at: datetime


class UserSummary(BaseModel):
    """Minimal public view of a user, used in lists and as post/comment author."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    avatar_url: str | None
    bio: str | None = None


class PublicProfile(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    bio: str | None
    avatar_url: str | None
    created_at: datetime
    followers_count: int
    following_count: int
    posts_count: int
    is_following: bool
    is_me: bool


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    bio: str | None = Field(default=None, max_length=300)

    @field_validator("display_name", "bio")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class UserPage(BaseModel):
    items: list[UserSummary]
    next_cursor: str | None
