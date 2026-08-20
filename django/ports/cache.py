from typing import Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    # ISP: minimal surface — services only need get/set/delete, not the full Redis command set
    def get(self, key: str) -> str | None:
        ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        ...

    def delete(self, key: str) -> None:
        ...
