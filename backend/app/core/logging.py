import logging
import os
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()
os.makedirs(settings.log_dir, exist_ok=True)

logger = logging.getLogger("rag_tien_gui_shb")
logger.setLevel(logging.INFO)

_fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

_file_handler = logging.FileHandler(
    os.path.join(settings.log_dir, f"app_{datetime.now():%Y%m%d}.log"), encoding="utf-8"
)
_file_handler.setFormatter(_fmt)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)

if not logger.handlers:
    logger.addHandler(_file_handler)
    logger.addHandler(_console_handler)


def log_conversation(session_id: str, role: str, content: str, meta: dict | None = None):
    """Ghi lại mọi lượt hội thoại để audit / đối soát sau này."""
    logger.info(f"[session={session_id}] [{role}] {content} | meta={meta or {}}")
