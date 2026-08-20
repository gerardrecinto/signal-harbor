package dev.gerard.signalharbor.signal;

public enum Severity {
    INFO(1),
    WARNING(3),
    CRITICAL(5);

    private final int weight;

    Severity(int weight) {
        this.weight = weight;
    }

    public int weight() {
        return weight;
    }
}
