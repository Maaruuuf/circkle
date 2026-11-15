"""Fixed-window rate limiting, backed by Redis (shared across all app instances).

Without REDIS_URL it falls back to process memory, which is fine for local
development and tests but NOT for several instances: each would count alone.
If Redis fails at runtime we fail open (log + allow) so a cache outage does not
take the whole API down.
"""

import asyncio
import logging
import time
from typing import Literal

from fastapi import Request
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.errors import RateLimitedError
from app.core.redis import get_redis
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)

_memory_hits: dict[str, tuple[int, float]] = {}
_memory_lock = asyncio.Lock()
_MEMORY_PRUNE_THRESHOLD = 10_000


def reset_memory_limits() -> None:
    _memory_hits.clear()


async def _hit(key: str, window_seconds: int, limit: int) -> tuple[int, int]:
    """Count one hit. Returns (hits_in_window, seconds_until_window_resets).

    Uses as few Redis commands as possible (1 per allowed request) because hosted Redis
    plans (e.g. Upstash free) are billed per command.
    """
    redis = get_redis()
    if redis is not None:
        try:
            count = int(await redis.incr(key))
            if count == 1:  # first hit: start the window
                await redis.expire(key, window_seconds)
                return count, window_seconds
            if count <= limit:  # allowed: nothing more to ask Redis
                return count, window_seconds
            ttl = int(await redis.ttl(key))  # blocked: we need the Retry-After value
            if ttl < 0:  # safety net: the key somehow lost its expiry
                await redis.expire(key, window_seconds)
                ttl = window_seconds
            return count, ttl
        except RedisError:
            logger.warning("rate limiter: redis unavailable, failing open")
            return 0, window_seconds

    now = time.monotonic()
    async with _memory_lock:
        if len(_memory_hits) > _MEMORY_PRUNE_THRESHOLD:
            for stale_key in [k for k, (_, reset) in _memory_hits.items() if reset <= now]:
                del _memory_hits[stale_key]
        count, reset_at = _memory_hits.get(key, (0, 0.0))
        if now >= reset_at:
            count, reset_at = 0, now + window_seconds
        count += 1
        _memory_hits[key] = (count, reset_at)
        return count, max(1, int(reset_at - now))


def client_ip(request: Request) -> str:
    settings = get_settings()
    if settings.trusted_proxy:
        # Behind a proxy we control (nginx, or Vercel -> Render) the FIRST X-Forwarded-For entry
        # is the real client: those proxies overwrite what the client sent.
        # Caveat: someone calling the backend URL directly (skipping the proxy) can fake it.
        forwarded_for = request.headers.get("x-forwarded-for", "")
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first[:64]
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip[:64]
    return request.client.host if request.client else "unknown"


class RateLimit:
    """FastAPI dependency: `Depends(RateLimit("login", limit=10, window_seconds=60))`."""

    def __init__(
        self,
        name: str,
        limit: int,
        window_seconds: int,
        per: Literal["ip", "user"] = "ip",
        skip_prefixes: tuple[str, ...] = (),
    ) -> None:
        self.name = name
        self.limit = limit
        self.window_seconds = window_seconds
        self.per = per
        self.skip_prefixes = skip_prefixes

    async def __call__(self, request: Request) -> None:
        if request.url.path.startswith(self.skip_prefixes) and self.skip_prefixes:
            return
        await self.check(self._identity(request))

    def _identity(self, request: Request) -> str:
        if self.per == "user":
            token = request.cookies.get("access_token")
            user_id = decode_access_token(token) if token else None
            if user_id is not None:
                return f"user:{user_id}"
        return f"ip:{client_ip(request)}"

    async def check(self, identity: str) -> None:
        """Count a hit for `identity` (e.g. an email address) and raise if over the limit."""
        if not get_settings().rate_limit_enabled:
            return
        count, retry_after = await _hit(
            f"rl:{self.name}:{identity}", self.window_seconds, self.limit
        )
        if count > self.limit:
            raise RateLimitedError(retry_after)
