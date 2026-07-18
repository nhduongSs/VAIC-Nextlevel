import shutil
import tempfile

import pytest

from app.infrastructure.storage.local_storage_provider import LocalStorageProvider


async def test_save_returns_posix_relative_path_and_read_accepts_windows_separator() -> None:
    tmp_dir = tempfile.mkdtemp()
    try:
        storage = LocalStorageProvider(tmp_dir)

        saved_path = await storage.save(b"docx bytes", "sample.docx")

        assert "\\" not in saved_path
        assert saved_path.endswith(".docx")
        assert await storage.read(saved_path) == b"docx bytes"
        assert await storage.read(saved_path.replace("/", "\\")) == b"docx bytes"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_absolute_path_rejects_traversal() -> None:
    tmp_dir = tempfile.mkdtemp()
    try:
        storage = LocalStorageProvider(tmp_dir)
        with pytest.raises(ValueError, match="Path traversal"):
            storage.get_absolute_path("../outside.docx")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
