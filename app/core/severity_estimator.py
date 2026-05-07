"""Pollution severity from scene coverage ratio (BR-AI-003 v1, master Phase 4)."""


def severity_from_pollution_coverage(
    ratio: float, *, thr_low: float, thr_med: float, thr_high: float
) -> str:
    """
    Map polluted-area / image-area ratio (0–1+) to ordinal severity.
    Master plan v1 thresholds: <5% Low; 5–15% Medium; 15–40% High; >40% Critical.
    """
    r = float(ratio)
    if r < thr_low:
        return "LOW"
    if r < thr_med:
        return "MEDIUM"
    if r < thr_high:
        return "HIGH"
    return "CRITICAL"
