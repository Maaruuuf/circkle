import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReactionType(StrEnum):
    LIKE = "like"
    LOVE = "love"
    HAHA = "haha"
    WOW = "wow"
    SAD = "sad"


class Reaction(Base):
    """At most one reaction per (post, user): the composite primary key enforces it."""

    __tablename__ = "reactions"
    __table_args__ = (
        CheckConstraint("type IN ('like', 'love', 'haha', 'wow', 'sad')", name="type_valid"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    type: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
