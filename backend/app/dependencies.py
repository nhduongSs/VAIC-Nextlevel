from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.base import get_db_session

# ── Database ─────────────────────────────────────────────────────────────────
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
