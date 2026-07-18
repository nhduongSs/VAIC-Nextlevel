"""Application factory — full FastAPI app from app/main.py, updated imports."""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import AppException
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.models.schemas import ErrorDetail, ErrorResponse

START_TIME = time.time()


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(settings.LOG_LEVEL)
    logger = structlog.get_logger(__name__)
    logger.info(
        "application_starting",
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.ENV,
    )
    yield
    logger.info("application_shutdown")
    await engine.dispose()


# ── OpenAPI patching ──────────────────────────────────────────────────────────


_ENUM_DESCRIPTIONS: dict[str, str] = {
    "DocumentType": (
        "Loại văn bản pháp lý:\n"
        "- `LAW` — Luật\n"
        "- `CIRCULAR` — Thông tư\n"
        "- `DECREE` — Nghị định\n"
        "- `DECISION` — Quyết định\n"
        "- `POLICY` — Chính sách nội bộ\n"
        "- `SOP` — Quy trình nghiệp vụ\n"
        "- `FAQ` — Hỏi đáp thường gặp\n"
        "- `PRODUCT_DOC` — Tài liệu sản phẩm\n"
        "- `MANUAL` — Sổ tay hướng dẫn\n"
        "- `UNKNOWN` — Chưa xác định được loại văn bản"
    ),
    "AuthorityLevel": (
        "Cấp thẩm quyền ban hành:\n"
        "- `NATIONAL_LAW` — Luật Quốc hội ban hành\n"
        "- `NHNN_CIRCULAR` — Thông tư Ngân hàng Nhà nước\n"
        "- `NHNN_DECISION` — Quyết định Ngân hàng Nhà nước\n"
        "- `INTERNAL_POLICY` — Chính sách nội bộ ngân hàng\n"
        "- `DEPARTMENT_SOP` — Quy trình cấp phòng ban\n"
        "- `FAQ` — Tài liệu hỏi đáp\n"
        "- `UNKNOWN` — Chưa xác định được cấp thẩm quyền"
    ),
}


def _patch_openapi(app: FastAPI) -> None:
    def patched_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description or "",
            routes=app.routes,
        )
        schemas: dict[str, Any] = schema.get("components", {}).get("schemas", {})
        for name, description in _ENUM_DESCRIPTIONS.items():
            if name in schemas:
                schemas[name]["description"] = description
        app.openapi_schema = schema
        return schema

    app.openapi = patched_openapi  # type: ignore[method-assign]


# ── Exception handlers ────────────────────────────────────────────────────────


def _register_exception_handlers(app: FastAPI) -> None:
    logger = structlog.get_logger(__name__)

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.warning(
            "app_exception",
            error=exc.error,
            message=exc.message,
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.error,
                message=exc.message,
                request_id=request_id,
            ).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        details = [
            ErrorDetail(
                field=".".join(str(loc) for loc in err["loc"]),
                message=err["msg"],
            )
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error="VALIDATION_ERROR",
                message="Request validation failed",
                request_id=request_id,
                details=details,
            ).model_dump(mode="json"),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.error("database_error", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                error="DATABASE_ERROR",
                message="A database error occurred",
                request_id=request_id,
            ).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.error("unhandled_exception", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="INTERNAL_ERROR",
                message="An unexpected error occurred",
                request_id=request_id,
            ).model_dump(mode="json"),
        )


# ── App factory ───────────────────────────────────────────────────────────────


async def _metrics() -> dict[str, object]:
    return {
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "environment": settings.ENV,
        "version": settings.APP_VERSION,
    }


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "**Hệ thống RAG văn bản pháp lý ngân hàng Việt Nam**\n\n"
            "API quản lý và xử lý văn bản pháp lý NHNN: upload tài liệu, "
            "trích xuất nội dung, tạo vector embedding (BGE-M3 1024 chiều) "
            "và tìm kiếm ngữ nghĩa phục vụ hỏi đáp tự động."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middleware (order matters — outermost added last)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )

    # Exception handlers
    _register_exception_handlers(app)

    # Routers (all sub-routers already registered in routes.py)
    app.include_router(router)
    app.add_api_route("/metrics", _metrics, include_in_schema=False)

    # OpenAPI enum descriptions
    _patch_openapi(app)

    return app


app = create_app()
