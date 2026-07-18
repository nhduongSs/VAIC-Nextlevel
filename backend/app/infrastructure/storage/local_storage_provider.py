import asyncio
import uuid
from pathlib import Path

from app.infrastructure.storage.storage_provider import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, upload_dir: str) -> None:
        self._upload_dir = Path(upload_dir)
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, content: bytes, original_filename: str) -> str:
        return await asyncio.to_thread(self._sync_save, content, original_filename)

    async def delete(self, path: str) -> None:
        await asyncio.to_thread(self._sync_delete, path)

    async def exists(self, path: str) -> bool:
        return await asyncio.to_thread(self._sync_exists, path)

    async def read(self, path: str) -> bytes:
        return await asyncio.to_thread(self._sync_read, path)

    def get_absolute_path(self, path: str) -> str:
        resolved = (self._upload_dir / path).resolve()
        root = self._upload_dir.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            raise ValueError(f"Path traversal detected: {path!r}") from None
        return str(resolved)

    # ── sync helpers (run inside to_thread) ──────────────────────────────────

    def _sync_save(self, content: bytes, original_filename: str) -> str:
        ext = Path(original_filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        subdir = unique_name[:2]
        dir_path = self._upload_dir / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / unique_name
        file_path.write_bytes(content)
        return (Path(subdir) / unique_name).as_posix()

    def _sync_delete(self, path: str) -> None:
        abs_path = Path(self.get_absolute_path(path))
        if abs_path.exists():
            abs_path.unlink()

    def _sync_exists(self, path: str) -> bool:
        return Path(self.get_absolute_path(path)).exists()

    def _sync_read(self, path: str) -> bytes:
        return Path(self.get_absolute_path(path)).read_bytes()
