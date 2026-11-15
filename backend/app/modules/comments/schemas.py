import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.users.schemas import UserSummary


class CreateCommentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content must not be blank")
        return value


class CommentResponse(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    content: str
    created_at: datetime
    author: UserSummary


class CommentPage(BaseModel):
    items: list[CommentResponse]
    next_cursor: str | None


CommentOrder = Literal["asc", "desc"]
