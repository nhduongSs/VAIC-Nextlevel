from abc import ABC, abstractmethod

from app.infrastructure.ingestion.parsed_document import ParsedDocument


class DocumentParser(ABC):
    """Abstraction for document format parsers."""

    @abstractmethod
    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """Parse raw file bytes into a structured ParsedDocument."""

    @property
    @abstractmethod
    def supported_content_types(self) -> list[str]:
        """Content-type strings this parser handles."""
