"""
PATTERN: Builder (Python implementation)

SignalBuilder constructs signal dicts with required fields enforced at
build() time and optional fields set fluently. Mirrors the Java Alert.Builder
but targets the dict-based signal contract used throughout the Python port.

Usage:
    signal = (
        SignalBuilder("payment-service", SignalType.ERROR_RATE_SPIKE, Severity.CRITICAL)
        .environment("production")
        .summary("Error rate 42% above baseline")
        .observed_at(datetime.now(timezone.utc))
        .build()
    )
"""

from __future__ import annotations

from datetime import UTC, datetime

from signal_harbor.domain.enums import Severity, SignalType


class SignalBuilder:

    def __init__(
        self,
        service_name: str,
        signal_type: SignalType,
        severity: Severity,
    ) -> None:
        # required
        self._service_name = service_name
        self._signal_type = signal_type
        self._severity = severity

        # optional — sensible defaults
        self._environment: str = "production"
        self._summary: str = ""
        self._observed_at: datetime = datetime.now(UTC)
        self._metadata: dict | None = None

    def environment(self, env: str) -> SignalBuilder:
        self._environment = env
        return self

    def summary(self, text: str) -> SignalBuilder:
        self._summary = text
        return self

    def observed_at(self, ts: datetime) -> SignalBuilder:
        self._observed_at = ts
        return self

    def metadata(self, data: dict) -> SignalBuilder:
        self._metadata = data
        return self

    def build(self) -> dict:
        if not self._service_name:
            raise ValueError("service_name required")
        payload: dict = {
            "service_name": self._service_name,
            "signal_type": self._signal_type.value,
            "severity": self._severity.value,
            "environment": self._environment,
            "summary": self._summary,
            "observed_at": self._observed_at,
        }
        if self._metadata is not None:
            payload["metadata"] = self._metadata
        return payload
