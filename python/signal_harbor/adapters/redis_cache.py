from typing import Optional

import redis


class RedisCache:
    # LSP: satisfies Cache Protocol — Redis-specific details are hidden behind the port surface
    # DIP: callers receive a Cache, never a RedisCache directly

    def __init__(self, redis_url: str) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._client.setex(key, ttl_seconds, value)

    def delete(self, key: str) -> None:
        self._client.delete(key)
