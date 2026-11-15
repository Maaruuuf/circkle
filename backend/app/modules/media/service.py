import asyncio
import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import PayloadTooLargeError
from app.modules.media.images import ProcessedImage, process_image
from app.modules.media.models import Media
from app.modules.media.storage import get_storage

CHUNK_SIZE = 64 * 1024


async def read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload without ever holding more than max_bytes + one chunk in memory."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(CHUNK_SIZE):
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLargeError(
                f"Image must be smaller than {get_settings().max_upload_mb} MB"
            )
        chunks.append(chunk)
    return b"".join(chunks)


class MediaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upload_image(
        self, owner_id: uuid.UUID, file: UploadFile, *, square: int | None = None
    ) -> Media:
        raw = await read_limited(file, get_settings().max_upload_bytes)
        # Image decoding is CPU-bound: keep it off the event loop.
        processed: ProcessedImage = await asyncio.to_thread(process_image, raw, square=square)

        key = f"{uuid.uuid4().hex}.webp"
        await get_storage().save(key, processed.data, processed.content_type)

        media = Media(
            owner_id=owner_id,
            key=key,
            content_type=processed.content_type,
            size_bytes=len(processed.data),
            width=processed.width,
            height=processed.height,
        )
        self._session.add(media)
        await self._session.commit()
        return media
