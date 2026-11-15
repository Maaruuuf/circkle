import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.rate_limit import RateLimit
from app.db.session import DbSession
from app.modules.auth.dependencies import CurrentUser
from app.modules.media.schemas import MediaResponse
from app.modules.media.service import MediaService
from app.modules.media.storage import LocalStorage, get_storage, media_url

# Upload API (versioned, authenticated)
router = APIRouter(prefix="/media", tags=["media"])
# Public file serving (unversioned URL so CDNs can cache it forever)
files_router = APIRouter(tags=["media"])

_FILENAME = re.compile(r"^[a-f0-9]{32}\.webp$")


@router.post(
    "/images",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit("upload", 30, 3600, per="user"))],
)
async def upload_image(
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP, max 5 MB")],
    user: CurrentUser,
    session: DbSession,
) -> MediaResponse:
    media = await MediaService(session).upload_image(user.id, file)
    return MediaResponse(
        id=media.id, url=media_url(media.key), width=media.width, height=media.height
    )


@files_router.get("/media/{filename}", include_in_schema=False)
async def serve_media(filename: str) -> FileResponse:
    storage = get_storage()
    if get_settings().storage_backend != "local" or not isinstance(storage, LocalStorage):
        raise NotFoundError("File not found")
    if not _FILENAME.fullmatch(filename):
        raise NotFoundError("File not found")
    path = storage.path_for(filename)
    if not path.is_file():
        raise NotFoundError("File not found")
    # Filenames are random and never reused, so the content can be cached forever.
    return FileResponse(
        path,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
