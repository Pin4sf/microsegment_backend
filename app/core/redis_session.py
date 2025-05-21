import json
import logging
from typing import Optional, Dict

import redis.asyncio as aioredis

from app.core.cache import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisSession:
    def __init__(
        self,
        redis_client_instance: aioredis.Redis,
        session_key_prefix: str = "session:",
        default_expire_ttl: int = settings.SESSION_DEFAULT_EXPIRE_TTL_SECONDS,
    ):
        self.redis_client = redis_client_instance
        self.session_key_prefix = session_key_prefix
        self.default_expire_ttl = default_expire_ttl

    async def get(self, session_id: str) -> Optional[Dict]:
        key = f"{self.session_key_prefix}{session_id}"
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting session {session_id} from Redis: {e}")
            return None

    async def set(self, session_id: str, data: Dict, expire_ttl: Optional[int] = None):
        key = f"{self.session_key_prefix}{session_id}"
        expire = expire_ttl if expire_ttl is not None else self.default_expire_ttl
        try:
            await self.redis_client.set(key, json.dumps(data), ex=expire)
        except Exception as e:
            logger.error(f"Error setting session {session_id} in Redis: {e}")

    async def delete(self, session_id: str):
        key = f"{self.session_key_prefix}{session_id}"
        try:
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Error deleting session {session_id} from Redis: {e}")


# Example of how to initialize (though actual initialization will be managed by dependency injection)
# session_manager = RedisSession(redis_client=redis_client)
