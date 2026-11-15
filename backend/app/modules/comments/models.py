import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin
from app.modules.users.models import User


class Comment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_post_id_created_at_id", "post_id", "created_at", "id"),)

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    author: Mapped[User] = relationship(lazy="raise")
