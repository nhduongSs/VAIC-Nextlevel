"""TokenEstimator — lightweight heuristic token counter.

Rule-of-thumb: 4 characters ≈ 1 token (reasonable for mixed Vietnamese/Latin text).
Intentionally avoids a full tokeniser dependency for hackathon speed.
"""
from __future__ import annotations

_CHARS_PER_TOKEN: float = 4.0


class TokenEstimator:
    """Estimates token counts without running a real tokeniser."""

    def estimate(self, text: str) -> int:
        """Return estimated token count for *text*."""
        return max(1, int(len(text) / _CHARS_PER_TOKEN))

    def estimate_prompt(self, system: str, user: str) -> int:
        """Return estimated token count for the combined system + user prompt.

        Adds a small overhead for message-framing tokens (≈ 10 per message).
        """
        return self.estimate(system) + self.estimate(user) + 20

    def estimate_completion(self, max_tokens: int) -> int:
        """Return a conservative estimate for completion tokens.

        Uses ``max_tokens`` as the upper bound since we cannot know the actual
        response length ahead of time.
        """
        return max_tokens
