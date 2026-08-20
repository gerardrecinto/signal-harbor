import uuid
from typing import ClassVar

from django.db import models


class Signal(models.Model):
    # SRP: pure data model — no business logic lives here
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_name = models.CharField(max_length=255, db_index=True)
    environment = models.CharField(max_length=64)
    signal_type = models.CharField(max_length=64)
    severity = models.CharField(max_length=16)
    observed_at = models.DateTimeField()
    summary = models.TextField()

    class Meta:
        db_table = "signals"
        ordering: ClassVar[list[str]] = ["-observed_at"]

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "service_name": self.service_name,
            "environment": self.environment,
            "signal_type": self.signal_type,
            "severity": self.severity,
            "observed_at": self.observed_at,
            "summary": self.summary,
        }
