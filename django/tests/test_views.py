import json
from datetime import UTC, datetime

import pytest

SIGNAL_PAYLOAD = {
    "service_name": "checkout",
    "environment": "prod",
    "signal_type": "DEPLOYMENT_FAILURE",
    "severity": "CRITICAL",
    "observed_at": datetime.now(tz=UTC).isoformat(),
    "summary": "Deployment to prod failed at rollout step 3",
}

INGEST_URL = "/api/v1/signals"
RISK_URL = "/api/v1/services/{service_name}/risk-summary"


@pytest.mark.django_db
def test_ingest_signal_returns_201(api_client):
    resp = api_client.post(
        INGEST_URL,
        data=json.dumps(SIGNAL_PAYLOAD),
        content_type="application/json",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["service_name"] == "checkout"
    assert body["severity"] == "CRITICAL"
    assert "id" in body


def test_health_returns_ok_without_api_key(client):
    # plain Django test client — no API key header, /health is outside /api/
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "UP"}


@pytest.mark.django_db
def test_ingest_requires_api_key(client):
    # plain Django test client — no API key header
    resp = client.post(
        INGEST_URL,
        data=json.dumps(SIGNAL_PAYLOAD),
        content_type="application/json",
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_ingest_rejects_invalid_severity(api_client):
    bad = {**SIGNAL_PAYLOAD, "severity": "MEGA_CRITICAL"}
    resp = api_client.post(
        INGEST_URL,
        data=json.dumps(bad),
        content_type="application/json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_risk_summary_no_signals_returns_low(api_client):
    resp = api_client.get(RISK_URL.format(service_name="unknown-svc"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_level"] == "LOW"
    assert body["score"] == 0


@pytest.mark.django_db
def test_risk_summary_three_critical_signals_returns_severe(api_client):
    for _ in range(3):
        api_client.post(
            INGEST_URL,
            data=json.dumps(SIGNAL_PAYLOAD),
            content_type="application/json",
        )
    resp = api_client.get(RISK_URL.format(service_name="checkout"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] == 15
    assert body["risk_level"] == "SEVERE"
    assert body["signal_count"] == 3


@pytest.mark.django_db
def test_risk_summary_cached_after_first_read(api_client):
    resp1 = api_client.get(RISK_URL.format(service_name="svc-a"))
    resp2 = api_client.get(RISK_URL.format(service_name="svc-a"))
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()


@pytest.mark.django_db
def test_risk_summary_cache_invalidated_after_ingest(api_client):
    # prime the cache with score=0
    resp1 = api_client.get(RISK_URL.format(service_name="checkout"))
    assert resp1.json()["score"] == 0

    # ingest a signal — should bust the cache key
    api_client.post(
        INGEST_URL,
        data=json.dumps(SIGNAL_PAYLOAD),
        content_type="application/json",
    )

    resp2 = api_client.get(RISK_URL.format(service_name="checkout"))
    assert resp2.json()["score"] > 0
