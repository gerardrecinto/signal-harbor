from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from signal_harbor.domain.enums import RiskLevel, Severity, SignalType


class CreateSignalRequest(BaseModel):
    model_config = ConfigDict()  # pydantic v2: ConfigDict instead of inner class Config

    service_name: str = Field(min_length=1, max_length=255)
    environment: str = Field(min_length=1, max_length=64)
    signal_type: SignalType
    severity: Severity
    observed_at: datetime
    summary: str = Field(min_length=1, max_length=800)


class SignalResponse(BaseModel):
    id: str
    service_name: str
    environment: str
    signal_type: SignalType
    severity: Severity
    observed_at: datetime
    summary: str


class RiskSummaryResponse(BaseModel):
    service_name: str
    risk_level: RiskLevel
    score: int
    signal_count: int
    lookback_hours: int
