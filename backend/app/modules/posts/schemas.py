import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.users.schemas import UserSummary


class CreatePostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str | None = Field(default=None, max_length=2000)
    # Id returned by POST /media/images (must be your own upload).
    media_id: uuid.UUID | None = None

    @field_validator("content")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class UpdatePostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content must not be blank")
        return value


class PostResponse(BaseModel):
    id: uuid.UUID
    content: str | None
    image_url: str | None
    created_at: datetime
    updated_at: datetime
    author: UserSummary
    reaction_count: int
    comment_count: int
    my_reaction: str | None


class PostPage(BaseModel):
    items: list[PostResponse]
    next_cursor: str | None
