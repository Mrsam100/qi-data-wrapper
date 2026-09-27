def calculate_quality_score(*, repaired_candle_count: int, provider_count: int) -> float:
    """Conservative MVP score; never awards unverified cross-source agreement."""
    score = 85.0  # complete canonical data from an approved primary source
    if provider_count > 1:
        score += 5.0  # a fallback contributed coverage, but is not a cross-check claim
    if repaired_candle_count:
        score -= min(10.0, repaired_candle_count * 0.1)
    return round(max(0.0, min(100.0, score)), 2)
