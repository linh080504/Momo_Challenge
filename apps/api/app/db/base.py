"""Kết nối DB. Đổi sang Postgres/Supabase chỉ cần đặt DATABASE_URL (và cài driver), không sửa code."""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """Supabase/Heroku đưa `postgres://`; SQLAlchemy 2 chỉ nhận `postgresql://`."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def make_engine(database_url: str) -> Engine:
    url = make_url(normalize_database_url(database_url))
    if url.get_backend_name() == "sqlite":
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        # FastAPI chạy endpoint sync trong thread pool → cho phép dùng kết nối khác thread.
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):  # SQLite mặc định KHÔNG bật khóa ngoại
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    from app.db import models  # noqa: F401 — đăng ký bảng vào metadata

    Base.metadata.create_all(engine)
