import os
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, status


@dataclass
class RateBucket:
    count: int
    reset_at: float


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, RateBucket] = {}

    def allow(self, key: str) -> tuple[bool, float]:
        now = time.time()
        bucket = self._buckets.get(key)
        if bucket is None or now >= bucket.reset_at:
            bucket = RateBucket(count=0, reset_at=now + self.window_seconds)
        if bucket.count >= self.max_requests:
            self._buckets[key] = bucket
            return False, max(0.0, bucket.reset_at - now)
        bucket.count += 1
        self._buckets[key] = bucket
        return True, max(0.0, bucket.reset_at - now)


def _rate_limit_key(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def _default_rate_limiter() -> RateLimiter:
    limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "90"))
    return RateLimiter(max_requests=limit, window_seconds=60)


rate_limiter = _default_rate_limiter()


def enforce_rate_limit(request: Request) -> None:
    allowed, retry_in = rate_limiter.allow(_rate_limit_key(request))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry in {int(retry_in)}s.",
        )
