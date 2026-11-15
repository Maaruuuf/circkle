import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.media.models import Media
from app.modules.users.models import User


class Post(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint(
            "media_id IS NOT NULL OR (content IS NOT NULL AND length(btrim(content)) > 0)",
            name="has_content_or_media",
        ),
        Index("ix_posts_author_id_created_at_id", "author_id", "created_at", "id"),
        Index("ix_posts_created_at_id", "created_at", "id"),
    )

    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str | None] = mapped_column(Text, default=None)
    media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), default=None
    )

    # lazy="raise": an accidental lazy load in async code fails loudly instead of
    # silently issuing N+1 queries. Queries must joinedload/contains_eager these.
    author: Mapped[User] = relationship(lazy="raise")
    media: Mapped[Media | None] = relationship(lazy="raise")
