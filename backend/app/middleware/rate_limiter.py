from fastapi import HTTPException, Request, status
from app.core.redis_client import get_redis
from app.core.config import settings
import time


async def rate_limit_middleware(request: Request, user_id: str):
    """
    Sliding window rate limiter backed by Redis.
    Two windows: per-minute and per-hour.
    """
    redis = await get_redis()
    now = int(time.time())

    minute_key = f"rl:minute:{user_id}:{now // 60}"
    hour_key = f"rl:hour:{user_id}:{now // 3600}"

    pipe = redis.pipeline()
    pipe.incr(minute_key)
    pipe.expire(minute_key, 70)
    pipe.incr(hour_key)
    pipe.expire(hour_key, 3700)
    results = await pipe.execute()

    minute_count, _, hour_count, _ = results

    if minute_count > settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {settings.RATE_LIMIT_PER_MINUTE} requests/minute",
            headers={"Retry-After": "60"},
        )

    if hour_count > settings.RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {settings.RATE_LIMIT_PER_HOUR} requests/hour",
            headers={"Retry-After": "3600"},
        )
