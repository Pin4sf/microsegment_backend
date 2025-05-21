# app/core/cache.py
from redis import Redis
from app.core.config import settings
from functools import wraps
from typing import Optional
from redis.exceptions import RedisError

redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_timeout=5
)


def cache_key_builder(*args, **kwargs) -> str:
    return f"{args}:{kwargs}"


def cache(ttl: int = 300):  # 5 minutes default
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = cache_key_builder(*args, **kwargs)
            cached = redis_client.get(key)
            if cached:
                return cached
            result = await func(*args, **kwargs)
            redis_client.setex(key, ttl, result)
            return result
        return wrapper
    return decorator

# error handling


class CacheError(Exception):
    pass


def safe_redis_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except RedisError as e:
            raise CacheError(f"Redis operation failed: {str(e)}")
    return wrapper
