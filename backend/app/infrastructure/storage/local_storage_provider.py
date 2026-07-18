"""LocalStorageProvider — stores files on the local filesystem."""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path


class LocalStorageProvider:
    """Saves, reads and deletes files under a configured base directory."""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes, filename: str) -> str:
        safe_name = Path(filename).name
        suffix = hashlib.sha256(data).hexdigest()[:8]
        stem = Path(safe_name).stem
        ext = Path(safe_name).suffix
        stored_name = f"{stem}_{suffix}{ext}"
        dest = self._base / stored_name
        await asyncio.to_thread(dest.write_bytes, data)
        return stored_name

    async def read(self, path: str) -> bytes:
        full = self._base / path
        return await asyncio.to_thread(full.read_bytes)

    async def delete(self, path: str) -> None:
        full = self._base / path
        if await asyncio.to_thread(full.exists):
            await asyncio.to_thread(full.unlink)
