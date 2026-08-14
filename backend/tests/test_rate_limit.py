from app.core.rate_limit import RedisRateLimiter


class FakeRedis:
    """Minimal INCR/EXPIRE stand-in — no live Redis in the test suite."""

    def __init__(self):
        self._counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        pass


async def test_allows_requests_up_to_the_limit():
    limiter = RedisRateLimiter(FakeRedis())
    for _ in range(3):
        assert await limiter.check("k", max_requests=3, window_seconds=60) is True


async def test_denies_requests_beyond_the_limit():
    limiter = RedisRateLimiter(FakeRedis())
    for _ in range(3):
        await limiter.check("k", max_requests=3, window_seconds=60)
    assert await limiter.check("k", max_requests=3, window_seconds=60) is False


async def test_different_keys_are_tracked_independently():
    limiter = RedisRateLimiter(FakeRedis())
    for _ in range(3):
        await limiter.check("user-a", max_requests=3, window_seconds=60)
    assert await limiter.check("user-b", max_requests=3, window_seconds=60) is True
