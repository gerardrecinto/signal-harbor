package dev.gerard.signalharbor.analytics;

import java.io.Serializable;
import java.time.Instant;
import java.util.Map;

// RiskScoringService caches this via @Cacheable(value = "riskSummaries", ...). Spring's default
// Redis cache serializer is JDK serialization, which throws at runtime for any non-Serializable
// payload. Without this, every risk-summary request 500s as soon as Redis caching is live.
public record RiskSummary(
        String serviceName,
        Instant windowStart,
        Instant windowEnd,
        int signalCount,
        int riskScore,
        RiskLevel riskLevel,
        Map<String, Long> signalsByType
) implements Serializable {
}
