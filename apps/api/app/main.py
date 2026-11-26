"""Khởi tạo ứng dụng. Chạy: `uvicorn app.main:create_app --factory` (xem docs/RUN_LOCAL.md)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, health, qr, reports
from app.core.config import Settings, load_settings
from app.core.errors import register_error_handlers
from app.core.middleware import BodySizeLimitMiddleware, RateLimitMiddleware, SlidingWindowLimiter
from app.db.base import init_db, make_engine, make_session_factory
from app.privacy.entities import EntityHasher
from app.services.schema import AnalysisValidator


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Trước Khi Chuyển — API", version=settings.app_version)

    # Không có khóa → dừng ngay lúc khởi động, TRƯỚC khi tạo file DB: hash ghi bằng khóa tạm/rỗng sẽ không sửa lại được.
    app.state.entity_hasher = EntityHasher(settings.entity_hash_key or "")
    engine = make_engine(settings.database_url)
    init_db(engine)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.analysis_validator = AnalysisValidator(settings.schema_path)  # thiếu file schema → lỗi ngay lúc khởi động
    app.state.limiter = SlidingWindowLimiter()

    register_error_handlers(app)

    # Thêm sau = bọc ngoài. Thứ tự từ ngoài vào: CORS → rate limit → giới hạn body → ứng dụng,
    # nên cả lỗi 429/413 cũng có header CORS để trình duyệt đọc được thông báo.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(RateLimitMiddleware, settings=settings, limiter=app.state.limiter)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["Retry-After"],
        allow_credentials=False,
    )

    app.include_router(health.router)
    app.include_router(analyze.router)
    app.include_router(qr.router)
    app.include_router(reports.router)
    return app
