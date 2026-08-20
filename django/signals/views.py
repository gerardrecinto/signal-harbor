from typing import ClassVar

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from signals import _services as _svc
from signals.serializers import (
    CreateSignalSerializer,
    RiskSummarySerializer,
    SignalResponseSerializer,
)


class SignalIngestView(APIView):
    # SRP: only handles signal ingestion requests — risk scoring is a separate view
    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = []

    def post(self, request: Request) -> Response:
        ser = CreateSignalSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        saved = _svc.ingestion.ingest(ser.validated_data)
        return Response(SignalResponseSerializer(saved).data, status=201)


class RiskSummaryView(APIView):
    # SRP: only handles risk summary reads — signal writes are a separate view
    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = []

    def get(self, request: Request, service_name: str) -> Response:
        summary = _svc.risk.get_risk_summary(service_name)
        return Response(RiskSummarySerializer(summary).data, status=200)


class HealthView(APIView):
    # Lives outside /api/, so ApiKeyMiddleware never touches it — same shape as
    # Java's actuator/health and FastAPI's /health, for orchestrator probes.
    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = []

    def get(self, request: Request) -> Response:
        return Response({"status": "UP"}, status=200)
