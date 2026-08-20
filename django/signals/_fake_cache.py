

class FakeCache:
    # LSP: satisfies Cache Protocol with an in-memory dict — substitutable for RedisCache in tests
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
