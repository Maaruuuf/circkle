import enum

from sqlalchemy import Boolean, CheckConstraint, Enum, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint("username = lower(username)", name="username_lowercase"),
        # Written once, explicitly. When you add a role to UserRole,
        # update this list in the same migration.
        CheckConstraint("role IN ('user', 'admin')", name="role_valid"),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=False,
            length=20,
            values_callable=lambda roles: [role.value for role in roles],
        ),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )