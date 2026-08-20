from datetime import UTC, datetime

from fastapi.testclient import TestClient

SIGNAL_PAYLOAD = {
    "service_name": "checkout",
    "environment": "prod",
    "signal_type": "DEPLOYMENT_FAILURE",
    "severity": "CRITICAL",
    "observed_at": datetime.now(tz=UTC).isoformat(),
    "summary": "Deployment to prod failed at rollout step 3",
}


def test_ingest_signal_returns_201(client: TestClient) -> None:
    resp = client.post("/api/v1/signals", json=SIGNAL_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["service_name"] == "checkout"
    assert body["severity"] == "CRITICAL"
    assert "id" in body


def test_ingest_signal_rejects_unknown_severity(client: TestClient) -> None:
    bad = {**SIGNAL_PAYLOAD, "severity": "UNKNOWN"}
    resp = client.post("/api/v1/signals", json=bad)
    assert resp.status_code == 422


def test_risk_summary_returns_correct_level(client: TestClient) -> None:
    # 3 CRITICAL signals → score=15 → SEVERE
    for _ in range(3):
        client.post("/api/v1/signals", json=SIGNAL_PAYLOAD)

    resp = client.get("/api/v1/services/checkout/risk-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service_name"] == "checkout"
    assert body["score"] == 15
    assert body["risk_level"] == "SEVERE"
    assert body["signal_count"] == 3


def test_risk_summary_low_when_no_signals(client: TestClient) -> None:
    resp = client.get("/api/v1/services/unknown-service/risk-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_level"] == "LOW"
    assert body["score"] == 0


def test_auth_rejection_without_api_key(client: TestClient) -> None:
    # send a request without the API key header
    resp = client.get(
        "/api/v1/services/checkout/risk-summary",
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 403


def test_auth_rejection_missing_header(client: TestClient) -> None:
    from starlette.testclient import TestClient as RawClient

    from signal_harbor.main import create_app

    app = create_app()
    with RawClient(app) as raw:
        resp = raw.get("/api/v1/services/checkout/risk-summary")
    assert resp.status_code == 403


def test_health_endpoint_requires_no_api_key(client: TestClient) -> None:
    from starlette.testclient import TestClient as RawClient

    from signal_harbor.main import create_app

    app = create_app()
    with RawClient(app) as raw:
        resp = raw.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "UP"}


def test_metrics_endpoint_exposes_prometheus_format(client: TestClient) -> None:
    from starlette.testclient import TestClient as RawClient

    from signal_harbor.main import create_app

    app = create_app()
    with RawClient(app) as raw:
        resp = raw.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
