"""
PATTERN: Singleton (Python implementation)

Thread-safe singleton using __new__ + a module-level lock.
Wraps a SQLAlchemy engine pool so the whole process shares one connection pool.

Why not just a module-level variable?
  Module-level singletons are process-unsafe when multiple threads race on the
  first import. The lock here guarantees exactly one engine is created even
  under concurrent startup (e.g. multiple Uvicorn workers in the same process).

Trade-off: FastAPI / SQLAlchemy already manage connection pools via the engine.
This class demonstrates the raw Singleton pattern for architecture reviews; in
production you'd rely on the engine's built-in pool (NullPool / QueuePool).
"""

from __future__ import annotations

import threading
from typing import Self

from sqlalchemy import Engine, create_engine, text

_lock = threading.Lock()


class DatabaseConnectionPool:
    _instance: DatabaseConnectionPool | None = None

    def __new__(cls, database_url: str = "", pool_size: int = 5) -> Self:
        if cls._instance is None:
            with _lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._engine: Engine = create_engine(
                        database_url,
                        pool_size=pool_size,
                        max_overflow=2,
                        pool_pre_ping=True,
                    )
                    obj._database_url = database_url
                    cls._instance = obj
        return cls._instance

    @property
    def engine(self) -> Engine:
        return self._engine

    def health_check(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001 - health check must report unhealthy on any failure
            return False

    @classmethod
    def _reset_for_testing(cls) -> None:
        """Test helper — never call in production."""
        with _lock:
            cls._instance = None
