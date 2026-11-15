"""Cache-aside helper: Redis when configured, tiny in-memory fallback otherwise.

Pattern used everywhere: read the cache, on a miss load from the database and
store with a TTL, and DELETE the key whenever the underlying data changes.
Cache failures never break a request.
"""

import json
import logging
import time
from typing import Any

from redis.exceptions import RedisError

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

_memory: dict[str, tuple[float, str]] = {}
_MEMORY_MAX_ITEMS = 5_000


def reset_memory_cache() -> None:
    _memory.clear()


async def cache_get_json(key: str) -> Any | None:
    redis = get_redis()
    if redis is not None:
        try:
            raw = await redis.get(key)
        except RedisError:
            logger.warning("cache: redis unavailable on get")
            return None
        return json.loads(raw) if raw is not None else None

    entry = _memory.get(key)
    if entry is None:
        return None
    expires_at, raw = entry
    if expires_at <= time.monotonic():
        _memory.pop(key, None)
        return None
    return json.loads(raw)


async def cache_set_json(key: str, value: Any, ttl_seconds: int) -> None:
    raw = json.dumps(value, default=str)
    redis = get_redis()
    if redis is not None:
        try:
            await redis.set(key, raw, ex=ttl_seconds)
        except RedisError:
            logger.warning("cache: redis unavailable on set")
        return
    if len(_memory) >= _MEMORY_MAX_ITEMS:
        _memory.clear()
    _memory[key] = (time.monotonic() + ttl_seconds, raw)


async def cache_delete(*keys: str) -> None:
    redis = get_redis()
    if redis is not None:
        try:
            await redis.delete(*keys)
        except RedisError:
            logger.warning("cache: redis unavailable on delete")
        return
    for key in keys:
        _memory.pop(key, None)
