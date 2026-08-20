package dev.gerard.signalharbor.analytics;

import dev.gerard.signalharbor.signal.ServiceSignal;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * PATTERN: Strategy — concrete implementation
 *
 * Score = sum of each signal's severity weight.
 * CRITICAL(5) > WARNING(3) > INFO(1).
 * This was the original hard-coded logic in RiskScoringService, now extracted.
 */
@Component("weightedRiskScoringStrategy")
public class WeightedRiskScoringStrategy implements RiskScoringStrategy {

    @Override
    public int computeScore(List<ServiceSignal> signals) {
        return signals.stream()
                .mapToInt(s -> s.getSeverity().weight())
                .sum();
    }
}
