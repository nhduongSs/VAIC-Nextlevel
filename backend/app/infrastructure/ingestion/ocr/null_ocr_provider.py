from app.infrastructure.ingestion.ocr.ocr_provider import OCRProvider


class NullOCRProvider(OCRProvider):
    """Placeholder OCR — returns empty string. Replace with Tesseract/PaddleOCR when needed."""

    async def extract_text(self, content: bytes) -> str:
        return ""

    def is_available(self) -> bool:
        return False
