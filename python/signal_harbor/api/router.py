from fastapi import APIRouter, Depends, Request, status

from signal_harbor.api.auth import require_api_key
from signal_harbor.api.metrics import risk_summaries_total
from signal_harbor.api.schemas import (
    CreateSignalRequest,
    RiskSummaryResponse,
    SignalResponse,
)
from signal_harbor.services.ingestion import SignalIngestionService
from signal_harbor.services.risk import RiskScoringService

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])


def _get_ingestion(request: Request) -> SignalIngestionService:
    # DIP: router never constructs services; state injected via app.state at startup
    return request.app.state.ingestion_service


def _get_risk(request: Request) -> RiskScoringService:
    return request.app.state.risk_service


@router.post("/signals", response_model=SignalResponse, status_code=status.HTTP_201_CREATED)
def ingest_signal(
    body: CreateSignalRequest,
    svc: SignalIngestionService = Depends(_get_ingestion),  # noqa: B008 - FastAPI DI idiom
) -> SignalResponse:
    # SRP: this handler's sole job is HTTP translation — business logic lives in the service
    saved = svc.ingest(body.model_dump())
    return SignalResponse(**saved)


@router.get(
    "/services/{service_name}/risk-summary",
    response_model=RiskSummaryResponse,
)
def get_risk_summary(
    service_name: str,
    svc: RiskScoringService = Depends(_get_risk),  # noqa: B008 - FastAPI DI idiom
) -> RiskSummaryResponse:
    # SRP: HTTP translation only; scoring and caching live in RiskScoringService
    risk_summaries_total.labels(service_name=service_name).inc()
    summary = svc.get_risk_summary(service_name)
    return RiskSummaryResponse(**summary)
