from redis.asyncio import Redis

from app.core.config import get_settings

_client: Redis | None = None


def get_redis() -> Redis | None:
    """Shared Redis client, or None when REDIS_URL is empty (in-memory fallbacks)."""
    global _client
    settings = get_settings()
    if not settings.redis_url:
        return None
    if _client is None:
        _client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
