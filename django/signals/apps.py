from django.apps import AppConfig


class SignalsConfig(AppConfig):
    name = "signals"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        # OCP: wiring happens here — adding a new adapter never changes service or view code
        # DIP: services receive abstractions; views only see _svc module, never concrete classes
        from django.conf import settings as django_settings

        from domain.risk_policy import WeightedRiskPolicy
        from services.ingestion import SignalIngestionService
        from services.risk import RiskScoringService
        from signals import _services as _svc
        from signals._fake_cache import FakeCache
        from signals._redis_cache import RedisCache
        from signals.orm_adapter import DjangoSignalRepository

        repo = DjangoSignalRepository()
        policy = WeightedRiskPolicy()

        try:
            cache = RedisCache(django_settings.SIGNAL_HARBOR_REDIS_URL)
        except Exception:  # noqa: BLE001 - fall back to in-memory cache on any startup failure
            cache = FakeCache()

        class _SettingsAdapter:
            # DIP: thin adapter exposes only what _RiskSettings Protocol requires
            risk_lookback_hours: int = django_settings.SIGNAL_HARBOR_RISK_LOOKBACK_HOURS
            cache_ttl_seconds: int = django_settings.SIGNAL_HARBOR_CACHE_TTL_SECONDS

        settings_adapter = _SettingsAdapter()

        _svc.ingestion = SignalIngestionService(writer=repo, cache=cache)
        _svc.risk = RiskScoringService(
            reader=repo,
            cache=cache,
            policy=policy,
            settings=settings_adapter,
        )
