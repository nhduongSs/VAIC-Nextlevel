from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.chunk import Chunk
from app.infrastructure.ingestion.parsed_document import ParsedDocument


def estimate_tokens(text: str) -> int:
    """Rough token estimate: whitespace-split word count."""
    return len(text.split())


class BaseChunker(ABC):
    """Abstract base for all chunking strategies."""

    @abstractmethod
    def chunk(self, document_id: UUID, parsed: ParsedDocument) -> list[Chunk]:
        """Produce ordered Chunk objects for a parsed document."""
