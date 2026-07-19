"""AuthService — xác thực email/mật khẩu, phát JWT access token."""

from __future__ import annotations

import structlog

from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, verify_password
from app.models.orm import UserModel
from app.repositories.user_store import PgUserRepository

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AuthService:
    def __init__(self, user_repo: PgUserRepository) -> None:
        self._repo = user_repo

    async def login(self, email: str, password: str) -> tuple[str, int, UserModel]:
        user = await self._repo.get_by_email(email)
        if (
            user is None
            or not user.is_active
            or not verify_password(password, user.hashed_password)
        ):
            logger.warning("login_failed", email=email)
            raise UnauthorizedException("Email hoặc mật khẩu không đúng")

        token, expires_in = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
            permissions=list(user.permissions),
        )
        logger.info(
            "login_success", user_id=str(user.id), email=user.email, role=user.role
        )
        return token, expires_in, user
