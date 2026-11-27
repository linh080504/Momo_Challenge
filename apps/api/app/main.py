import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from .analyzer.agents.analyze import Analyzer
from .analyzer.contract import AnalyzerError
from .api.routes import make_routes
from .auth.security import Limits, Signer
from .config import Settings
from .db.store import Base, Store
from .evidence.safe_browsing import SafeBrowsing


def create_app(settings=None):
    settings = settings or Settings()
    pairs = [
        (settings.demo_user_email.strip().lower(), settings.demo_user_password, "user"),
        (settings.demo_ops_email.strip().lower(), settings.demo_ops_password, "ops"),
    ]
    users = {email: (password, role) for email, password, role in pairs if email and password}
    if len(users) != sum(bool(email and password) for email, password, _ in pairs):
        raise RuntimeError("Tài khoản người dùng và vận hành cần email riêng.")
    if any(bool(email) != bool(password) for email, password, _ in pairs):
        raise RuntimeError("Mỗi tài khoản cần cả email và mật khẩu.")
    if (users or not settings.database_url.startswith("sqlite")) and len(settings.app_secret) < 32:
        raise RuntimeError("Cấu hình APP_SECRET dài ít nhất 32 ký tự để dùng tài khoản hoặc PostgreSQL.")
    signer = Signer(settings.app_secret or secrets.token_urlsafe(48))
    store = Store(settings.database_url)
    limits = Limits()

    @asynccontextmanager
    async def lifespan(_app):
        try:
            if store.engine.dialect.name == "postgresql":
                def check_migration():
                    tables = set(inspect(store.engine).get_table_names(schema="tkc"))
                    if not set(Base.metadata.tables).issubset(tables):
                        raise RuntimeError("Chạy các migration trong infra/supabase/migrations trước khi khởi động.")
                await run_in_threadpool(check_migration)
            else:
                await run_in_threadpool(Base.metadata.create_all, store.engine)
            yield
        finally:
            await run_in_threadpool(store.engine.dispose)

    app = FastAPI(title="Trước Khi Chuyển", version=settings.app_version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",")],
        allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def privacy_headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request, _error):
        return JSONResponse({"detail": "Dữ liệu gửi lên không đúng định dạng."}, status_code=422)

    @app.exception_handler(AnalyzerError)
    async def bad_analysis(_request, error):
        return JSONResponse({"detail": error.message}, status_code=error.status)

    @app.exception_handler(SQLAlchemyError)
    async def unavailable_store(_request, _error):
        return JSONResponse({"detail": "Dịch vụ đang gián đoạn. Hãy thử lại."}, status_code=503)

    analyzer = Analyzer(settings, store, signer, limits, SafeBrowsing(settings.safe_browsing_key))
    app.include_router(make_routes(settings, store, signer, limits, users, analyzer))
    return app


app = create_app()
