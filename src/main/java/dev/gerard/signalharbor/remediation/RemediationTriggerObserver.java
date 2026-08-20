package dev.gerard.signalharbor.remediation;

import dev.gerard.signalharbor.analytics.RiskLevel;
import dev.gerard.signalharbor.signal.ServiceSignal;
import dev.gerard.signalharbor.signal.Severity;
import dev.gerard.signalharbor.signal.SignalObserver;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * PATTERN: Observer — concrete subscriber (implementation pattern)
 *               + Builder — uses Alert.Builder to construct the alert
 *
 * Reacts to ingested signals. Fires an Alert (built via Alert.Builder) for any
 * CRITICAL or WARNING signal and logs it. Real implementations would POST to
 * PagerDuty, publish to SNS, etc.
 */
@Component
public class RemediationTriggerObserver implements SignalObserver {

    private static final Logger log = LoggerFactory.getLogger(RemediationTriggerObserver.class);

    @Override
    public void onSignalIngested(ServiceSignal signal) {
        if (signal.getSeverity().weight() < Severity.WARNING.weight()) {
            return;
        }

        RiskLevel level = signal.getSeverity() == Severity.CRITICAL
                ? RiskLevel.SEVERE
                : RiskLevel.HIGH;

        Alert alert = new Alert.Builder(signal.getServiceName(), level)
                .triggeredAt(Instant.now())
                .signalType(signal.getSignalType())
                .message(signal.getSummary())
                .oncallTeam(signal.getServiceName() + "-oncall")
                .pagerDutyEnabled(signal.getSeverity() == Severity.CRITICAL)
                .build();

        log.warn("[REMEDIATION] {}", alert);
    }
}
