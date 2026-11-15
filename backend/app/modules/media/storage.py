import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class Storage(Protocol):
    async def save(self, key: str, data: bytes, content_type: str) -> None: ...

    async def delete(self, key: str) -> None: ...


class LocalStorage:
    """Files on disk. Fine for one server; for several app servers use a shared
    volume (docker-compose.prod.yml does this) or switch to S3-compatible storage."""

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents:  # defence against path traversal
            raise ValueError("invalid storage key")
        return path

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self.path_for(key)
        await asyncio.to_thread(path.write_bytes, data)

    async def delete(self, key: str) -> None:
        path = self.path_for(key)
        await asyncio.to_thread(path.unlink, True)


class S3Storage:
    """Any S3-compatible service: AWS S3, Cloudflare R2, MinIO, Backblaze B2."""

    def __init__(self) -> None:
        import boto3  # imported lazily so local-only setups never load it
        from botocore.config import Config

        settings = get_settings()
        self._bucket = settings.s3_bucket
        options: dict[str, object] = {
            "signature_version": "s3v4",
            "s3": {"addressing_style": "path"},  # what Supabase / MinIO / R2 expect
        }
        try:
            # Newer botocore adds extra checksums that some S3-compatible services reject.
            config = Config(
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                **options,
            )
        except TypeError:  # older botocore does not know these settings
            config = Config(**options)
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
            config=config,
        )

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage(settings.media_root)


def media_url(key: str) -> str:
    """Public URL of a stored file: CDN/bucket URL if configured, else our /media route."""
    base = get_settings().media_public_base_url.rstrip("/")
    return f"{base}/{key}" if base else f"/media/{key}"
