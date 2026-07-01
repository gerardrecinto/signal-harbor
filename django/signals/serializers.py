from rest_framework import serializers

from domain.enums import Severity, SignalType


class CreateSignalSerializer(serializers.Serializer):
    service_name = serializers.CharField(max_length=255)
    environment = serializers.CharField(max_length=64)
    signal_type = serializers.ChoiceField(choices=[(t.value, t.value) for t in SignalType])
    severity = serializers.ChoiceField(choices=[(s.value, s.value) for s in Severity])
    observed_at = serializers.DateTimeField()
    summary = serializers.CharField(max_length=800)


class SignalResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    service_name = serializers.CharField()
    environment = serializers.CharField()
    signal_type = serializers.CharField()
    severity = serializers.CharField()
    observed_at = serializers.DateTimeField()
    summary = serializers.CharField()


class RiskSummarySerializer(serializers.Serializer):
    service_name = serializers.CharField()
    risk_level = serializers.CharField()
    score = serializers.IntegerField()
    signal_count = serializers.IntegerField()
    lookback_hours = serializers.IntegerField()
