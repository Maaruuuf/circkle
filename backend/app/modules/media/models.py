import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


class Media(UUIDPrimaryKeyMixin, Base):
    """Metadata for an uploaded image. The bytes live in object storage / on disk."""

    __tablename__ = "media"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
