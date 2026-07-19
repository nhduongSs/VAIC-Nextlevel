"""Password hashing and JWT helpers.

Uses `bcrypt` directly instead of `passlib.CryptContext` — the pinned
passlib==1.7.4 fails to detect bcrypt>=4.0's version marker
(`module 'bcrypt' has no attribute '__about__'`), so CryptContext.hash()
raises. Calling bcrypt.hashpw/checkpw directly sidesteps that bug.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(
    user_id: UUID,
    email: str,
    role: str,
    permissions: list[str],
) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(UTC) + expires_delta
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "permissions": permissions,
        "exp": expire,
    }
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
    return payload
