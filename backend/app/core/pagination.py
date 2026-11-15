"""Cursor (keyset) pagination.

Offset pagination gets slower on deep pages and skips/duplicates rows when data
changes while the user scrolls. A keyset cursor points at the last row seen:
"give me rows older than (created_at, id)". It is stable and index-friendly.
"""

import base64
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import Select, and_, or_
from sqlalchemy.orm import InstrumentedAttribute

from app.core.errors import BadRequestError

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50


@dataclass(frozen=True)
class Cursor:
    created_at: datetime
    id: uuid.UUID


def encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{row_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(value: str | None) -> Cursor | None:
    if not value:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        created_part, id_part = raw.split("|", 1)
        created_at = datetime.fromisoformat(created_part)
        if created_at.tzinfo is None:
            raise ValueError("cursor timestamp must be timezone-aware")
        return Cursor(created_at=created_at, id=uuid.UUID(id_part))
    except (ValueError, UnicodeDecodeError):
        raise BadRequestError("Invalid pagination cursor", code="INVALID_CURSOR") from None


def apply_keyset(
    stmt: Select[Any],
    created_col: InstrumentedAttribute[datetime],
    id_col: InstrumentedAttribute[uuid.UUID],
    cursor: Cursor | None,
    *,
    descending: bool = True,
) -> Select[Any]:
    """Add the WHERE clause for 'rows after the cursor'. You still add ORDER BY yourself."""
    if cursor is None:
        return stmt
    if descending:
        condition = or_(
            created_col < cursor.created_at,
            and_(created_col == cursor.created_at, id_col < cursor.id),
        )
    else:
        condition = or_(
            created_col > cursor.created_at,
            and_(created_col == cursor.created_at, id_col > cursor.id),
        )
    return stmt.where(condition)


def build_page(
    rows: Sequence[T], limit: int, cursor_of: Callable[[T], str]
) -> tuple[list[T], str | None]:
    """`rows` must have been fetched with LIMIT limit + 1 to detect a next page."""
    has_more = len(rows) > limit
    items = list(rows[:limit])
    next_cursor = cursor_of(items[-1]) if has_more and items else None
    return items, next_cursor
