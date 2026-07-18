"""StorageProvider protocol — abstracts file persistence."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageProvider(Protocol):
    async def save(self, data: bytes, filename: str) -> str: ...

    async def read(self, path: str) -> bytes: ...

    async def delete(self, path: str) -> None: ...
