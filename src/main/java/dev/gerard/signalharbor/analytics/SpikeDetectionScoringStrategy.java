package dev.gerard.signalharbor.analytics;

import dev.gerard.signalharbor.signal.ServiceSignal;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * PATTERN: Strategy — alternate concrete implementation
 *
 * Applies a spike multiplier when signal volume exceeds a threshold, on top of
 * the weighted base score. Models the idea that a burst of even INFO signals can
 * indicate an underlying incident.
 *
 * score = weighted_sum * (1 + spike_factor * max(0, count - spike_threshold))
 *
 * Example: 20 INFO signals → base 20, spike_threshold=10 → 20 * (1 + 0.5*10) = 120 → SEVERE
 */
@Component("spikeDetectionScoringStrategy")
public class SpikeDetectionScoringStrategy implements RiskScoringStrategy {

    private final int spikeThreshold;
    private final double spikeFactor;

    public SpikeDetectionScoringStrategy() {
        this(10, 0.5);
    }

    SpikeDetectionScoringStrategy(int spikeThreshold, double spikeFactor) {
        this.spikeThreshold = spikeThreshold;
        this.spikeFactor = spikeFactor;
    }

    @Override
    public int computeScore(List<ServiceSignal> signals) {
        int base = signals.stream()
                .mapToInt(s -> s.getSeverity().weight())
                .sum();

        int excess = Math.max(0, signals.size() - spikeThreshold);
        double multiplier = 1.0 + spikeFactor * excess;
        return (int) (base * multiplier);
    }
}
