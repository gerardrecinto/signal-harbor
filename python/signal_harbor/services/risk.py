import json
from datetime import datetime, timedelta, timezone

from signal_harbor.config import Settings
from signal_harbor.domain.risk_policy import RiskPolicy
from signal_harbor.ports.cache import Cache
from signal_harbor.ports.signal_reader import SignalReader


class RiskScoringService:
    # SRP: only computes and caches risk summaries — never writes signals
    # DIP: depends on Protocol abstractions (SignalReader, Cache, RiskPolicy, Settings)

    def __init__(
        self,
        reader: SignalReader,
        cache: Cache,
        policy: RiskPolicy,
        settings: Settings,
    ) -> None:
        self._reader = reader
        self._cache = cache
        self._policy = policy
        self._settings = settings

    def get_risk_summary(self, service_name: str) -> dict:
        cache_key = f"risk:{service_name.lower()}"
        cached = self._cache.get(cache_key)
        if cached:
            return json.loads(cached)

        after = datetime.now(tz=timezone.utc) - timedelta(
            hours=self._settings.risk_lookback_hours
        )
        signals = self._reader.find_by_service_after(service_name, after)

        # OCP: policy is injected — swap WeightedRiskPolicy for any RiskPolicy subclass
        score, level = self._policy.compute_level(signals)

        summary = {
            "service_name": service_name,
            "risk_level": level.value,
            "score": score,
            "signal_count": len(signals),
            "lookback_hours": self._settings.risk_lookback_hours,
        }

        self._cache.set(cache_key, json.dumps(summary), self._settings.cache_ttl_seconds)
        return summary
