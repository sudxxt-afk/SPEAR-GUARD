import os
import json
from typing import Optional, Any
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool
import logging

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
REDIS_DECODE_RESPONSES = True


class RedisClient:
    """
    Async Redis client wrapper for SPEAR-GUARD
    Handles caching, session storage, and pub/sub
    """

    def __init__(self):
        self.pool = ConnectionPool.from_url(
            REDIS_URL,
            max_connections=REDIS_MAX_CONNECTIONS,
            decode_responses=REDIS_DECODE_RESPONSES,
        )
        self.redis: Optional[Redis] = None

    async def connect(self):
        """
        Initialize Redis connection
        """
        if not self.redis:
            self.redis = Redis(connection_pool=self.pool)
            logger.info(f"Redis connected: {REDIS_URL}")

    async def close(self):
        """
        Close Redis connection
        """
        if self.redis:
            await self.redis.close()
            await self.pool.disconnect()
            logger.info("Redis connection closed")

    async def ping(self) -> bool:
        """
        Check if Redis is alive
        """
        if not self.redis:
            await self.connect()
        return await self.redis.ping()

    # Cache operations
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from cache
        """
        if not self.redis:
            await self.connect()
        return await self.redis.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        nx: bool = False,
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if not string)
            ex: Expiration time in seconds
            nx: Only set if key doesn't exist
        """
        if not self.redis:
            await self.connect()

        if not isinstance(value, str):
            value = json.dumps(value)

        return await self.redis.set(key, value, ex=ex, nx=nx)

    async def setex(self, key: str, seconds: int, value: Any) -> bool:
        """
        Set value with expiration time
        """
        return await self.set(key, value, ex=seconds)

    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys
        """
        if not self.redis:
            await self.connect()
        return await self.redis.delete(*keys)

    async def exists(self, key: str) -> bool:
        """
        Check if key exists
        """
        if not self.redis:
            await self.connect()
        return await self.redis.exists(key) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for key
        """
        if not self.redis:
            await self.connect()
        return await self.redis.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for key
        """
        if not self.redis:
            await self.connect()
        return await self.redis.ttl(key)

    # Hash operations
    async def hget(self, name: str, key: str) -> Optional[str]:
        """
        Get value from hash
        """
        if not self.redis:
            await self.connect()
        return await self.redis.hget(name, key)

    async def hset(self, name: str, key: str, value: Any) -> int:
        """
        Set value in hash
        """
        if not self.redis:
            await self.connect()

        if not isinstance(value, str):
            value = json.dumps(value)

        return await self.redis.hset(name, key, value)

    async def hgetall(self, name: str) -> dict:
        """
        Get all fields from hash
        """
        if not self.redis:
            await self.connect()
        return await self.redis.hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        """
        Delete fields from hash
        """
        if not self.redis:
            await self.connect()
        return await self.redis.hdel(name, *keys)

    # List operations
    async def lpush(self, name: str, *values: Any) -> int:
        """
        Push values to the left of list
        """
        if not self.redis:
            await self.connect()
        return await self.redis.lpush(name, *values)

    async def rpush(self, name: str, *values: Any) -> int:
        """
        Push values to the right of list
        """
        if not self.redis:
            await self.connect()
        return await self.redis.rpush(name, *values)

    async def lpop(self, name: str) -> Optional[str]:
        """
        Pop value from the left of list
        """
        if not self.redis:
            await self.connect()
        return await self.redis.lpop(name)

    async def lrange(self, name: str, start: int, end: int) -> list:
        """
        Get range of values from list
        """
        if not self.redis:
            await self.connect()
        return await self.redis.lrange(name, start, end)

    # Pub/Sub operations
    async def publish(self, channel: str, message: Any) -> int:
        """
        Publish message to channel
        """
        if not self.redis:
            await self.connect()

        if not isinstance(message, str):
            message = json.dumps(message)

        return await self.redis.publish(channel, message)

    # SPEAR-GUARD specific cache methods
    async def cache_analysis(self, message_id: str, analysis: dict, ttl: int = 900):
        """
        Cache email analysis result (15 minutes default)
        """
        key = f"analysis:{message_id}"
        return await self.setex(key, ttl, analysis)

    async def get_cached_analysis(self, message_id: str) -> Optional[dict]:
        """
        Get cached email analysis
        """
        key = f"analysis:{message_id}"
        data = await self.get(key)
        return json.loads(data) if data else None

    async def cache_registry_lookup(self, email: str, result: dict, ttl: int = 3600):
        """
        Cache trusted registry lookup (1 hour default)
        """
        key = f"registry:{email}"
        return await self.setex(key, ttl, result)

    async def get_cached_registry(self, email: str) -> Optional[dict]:
        """
        Get cached registry lookup
        """
        key = f"registry:{email}"
        data = await self.get(key)
        return json.loads(data) if data else None

    async def increment_counter(self, key: str, amount: int = 1) -> int:
        """
        Increment counter
        """
        if not self.redis:
            await self.connect()
        return await self.redis.incrby(key, amount)

    async def get_counter(self, key: str) -> int:
        """
        Get counter value
        """
        value = await self.get(key)
        return int(value) if value else 0

    # Distributed lock operations
    async def setnx_with_ttl(self, key: str, value: Any, seconds: int) -> bool:
        """
        Set key only if it doesn't exist (atomic), with TTL.
        Returns True if lock was acquired, False if key already exists.
        """
        if not self.redis:
            await self.connect()
        if not isinstance(value, str):
            value = json.dumps(value)
        return await self.redis.set(key, value, nx=True, ex=seconds)

    async def release_lock(self, key: str) -> bool:
        """
        Release a lock (delete key). Use with caution — only release locks you own.
        Returns True if the lock was deleted.
        """
        if not self.redis:
            await self.connect()
        return await self.redis.delete(key) > 0


# Global Redis client instance
redis_client = RedisClient()


# Helper functions
async def get_redis() -> RedisClient:
    """
    Dependency for FastAPI to get Redis client
    """
    if not redis_client.redis:
        await redis_client.connect()
    return redis_client


def get_redis_sync() -> RedisClient:
    """
    Synchronous helper to get Redis client for Celery tasks (non-async context).
    Returns the global redis_client instance.
    """
    return redis_client


if __name__ == "__main__":
    import asyncio

    async def test_redis():
        # Test connection
        await redis_client.connect()
        print("✓ Redis connected")

        # Test ping
        pong = await redis_client.ping()
        print(f"✓ Ping: {pong}")

        # Test set/get
        await redis_client.set("test_key", "test_value", ex=10)
        value = await redis_client.get("test_key")
        print(f"✓ Set/Get: {value}")

        # Test cache analysis
        test_analysis = {
            "message_id": "test123",
            "risk_score": 75,
            "status": "warning"
        }
        await redis_client.cache_analysis("test123", test_analysis)
        cached = await redis_client.get_cached_analysis("test123")
        print(f"✓ Cache analysis: {cached}")

        # Close connection
        await redis_client.close()
        print("✓ Redis connection closed")

    asyncio.run(test_redis())
