from abc import ABC, abstractmethod


class OCRProvider(ABC):
    """Abstraction for optical character recognition."""

    @abstractmethod
    async def extract_text(self, content: bytes) -> str:
        """Extract text from image or scanned PDF bytes."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the OCR backend is ready."""
