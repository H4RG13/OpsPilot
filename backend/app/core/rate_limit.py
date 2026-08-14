from functools import lru_cache
from typing import Protocol

import redis.asyncio as redis
from fastapi import Depends

from app.core.config import settings
from app.modules.auth.dependencies import AuthContext, get_current_context
from app.shared.exceptions import RateLimitError


class RateLimiter(Protocol):
    async def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Return True if this call is allowed, False if the caller is over the limit."""
        ...


class RedisRateLimiter:
    """Fixed-window counter: INCR the window's key, set its TTL on first use."""

    def __init__(self, client: redis.Redis):
        self._client = client

    async def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        current = await self._client.incr(key)
        if current == 1:
            await self._client.expire(key, window_seconds)
        return current <= max_requests


@lru_cache
def get_rate_limiter() -> RateLimiter:
    client = redis.from_url(settings.redis_url)
    return RedisRateLimiter(client)


def rate_limit(scope: str, max_requests: int, window_seconds: int):
    """Dependency factory: per-user, per-organization fixed-window rate limit.
    Raises RateLimitError (429) once the caller exceeds max_requests within
    window_seconds. Used on AI endpoints to control abuse and cost (spec
    Sections 14, 25)."""

    async def _check(
        context: AuthContext = Depends(get_current_context),
        limiter: RateLimiter = Depends(get_rate_limiter),
    ) -> None:
        key = f"ratelimit:{scope}:{context.organization_id}:{context.user.id}"
        allowed = await limiter.check(key, max_requests, window_seconds)
        if not allowed:
            raise RateLimitError(
                f"Rate limit exceeded for {scope}. Try again later.", code="RATE_LIMITED"
            )

    return _check
