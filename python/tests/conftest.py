import uuid

import pytest
from fastapi.testclient import TestClient

from signal_harbor.adapters.postgres import (
    PostgresSignalRepository,
    build_session_factory,
)
from signal_harbor.config import Settings
from signal_harbor.domain.risk_policy import WeightedRiskPolicy
from signal_harbor.main import create_app
from signal_harbor.services.ingestion import SignalIngestionService
from signal_harbor.services.risk import RiskScoringService


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


@pytest.fixture()
def settings() -> Settings:
    # each test gets a unique DB name so shared-cache in-memory DBs stay isolated
    db_name = f"testdb_{uuid.uuid4().hex}"
    return Settings(
        database_url=f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        api_key="test-key",
        risk_lookback_hours=24,
        cache_ttl_seconds=60,
    )


@pytest.fixture()
def fake_cache() -> FakeCache:
    return FakeCache()


@pytest.fixture()
def repo(settings: Settings) -> PostgresSignalRepository:
    factory = build_session_factory(settings.database_url)
    return PostgresSignalRepository(factory)


@pytest.fixture()
def client(settings: Settings, fake_cache: FakeCache, repo: PostgresSignalRepository) -> TestClient:
    app = create_app()

    # override lifespan wiring with test doubles — DIP makes this seamless
    policy = WeightedRiskPolicy()
    with TestClient(app, raise_server_exceptions=True) as c:
        # lifespan already ran with default Settings; overwrite state for test isolation
        app.state.api_key = settings.api_key
        app.state.ingestion_service = SignalIngestionService(writer=repo, cache=fake_cache)
        app.state.risk_service = RiskScoringService(
            reader=repo, cache=fake_cache, policy=policy, settings=settings
        )
        c.headers.update({"X-API-Key": settings.api_key})
        yield c
