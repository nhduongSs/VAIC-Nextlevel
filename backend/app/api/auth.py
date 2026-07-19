"""Auth endpoints — đăng nhập, phát JWT access token."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import AuthServiceDep, CurrentUserDep
from app.models.orm import UserModel
from app.models.schemas import LoginRequest, LoginResponse, UserResponse
from app.utils.constants import API_V1_PREFIX

router = APIRouter(prefix=f"{API_V1_PREFIX}/auth", tags=["Auth"])


def _to_user_response(user: UserModel) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        permissions=list(user.permissions),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Đăng nhập bằng email/mật khẩu, nhận JWT access token",
)
async def login(body: LoginRequest, service: AuthServiceDep) -> LoginResponse:
    token, expires_in, user = await service.login(body.email, body.password)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=_to_user_response(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Thông tin user hiện tại (giải mã từ access token)",
)
async def me(current_user: CurrentUserDep) -> UserResponse:
    return _to_user_response(current_user)
