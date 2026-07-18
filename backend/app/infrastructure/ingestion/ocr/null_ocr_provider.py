"""NullOCRProvider — no-op OCR that passes content through unchanged."""
from __future__ import annotations


class NullOCRProvider:
    """OCR provider that performs no processing (stub for non-scanned documents)."""

    async def extract_text(self, image_data: bytes) -> str:
        return ""
