

class RedisCache:
    # LSP: satisfies Cache Protocol — substitutable for FakeCache in production
    # DIP: wraps redis client behind the Cache port interface

    def __init__(self, url: str) -> None:
        import redis

        self._client = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> str | None:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._client.setex(key, ttl_seconds, value)

    def delete(self, key: str) -> None:
        self._client.delete(key)
