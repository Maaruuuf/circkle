import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint("username = lower(username)", name="username_lowercase"),
        # When you add a role to UserRole, update this list in the same migration.
        CheckConstraint("role IN ('user', 'admin')", name="role_valid"),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)
    display_name: Mapped[str] = mapped_column(String(50))
    bio: Mapped[str | None] = mapped_column(String(300), default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(500), default=None)
    # NULL for accounts created through Google login (no password set yet).
    password_hash: Mapped[str | None] = mapped_column(String(255), default=None)
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    role: Mapped[str] = mapped_column(
        String(20), default=UserRole.USER.value, server_default=UserRole.USER.value
    )
    # is_active is controlled by admins (ban). deactivated_at is the user's own choice.
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (
        CheckConstraint("follower_id <> followee_id", name="no_self_follow"),
        Index("ix_follows_followee_id_created_at", "followee_id", "created_at"),
        Index("ix_follows_follower_id_created_at", "follower_id", "created_at"),
    )

    follower_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    followee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
