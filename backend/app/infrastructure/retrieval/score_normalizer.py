from __future__ import annotations


def min_max_normalize(scores: list[float]) -> list[float]:
    """Scale scores to [0, 1] using min-max normalization.

    If all scores are equal, returns a list of 1.0s (non-zero rank signal).
    """
    if not scores:
        return []
    min_s = min(scores)
    max_s = max(scores)
    if max_s == min_s:
        return [1.0] * len(scores)
    span = max_s - min_s
    return [(s - min_s) / span for s in scores]
