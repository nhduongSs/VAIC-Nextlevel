from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    async def save(self, content: bytes, original_filename: str) -> str:
        """Persist content and return the storage-relative path."""

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Remove the file at the given storage path."""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Return True if the file exists at the given storage path."""

    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Read and return the file content at the given storage path."""

    @abstractmethod
    def get_absolute_path(self, path: str) -> str:
        """Resolve the storage path to an absolute filesystem path."""
