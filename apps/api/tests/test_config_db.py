import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from app.core.config import DEFAULT_ORIGINS, load_settings
from app.db.base import make_engine, normalize_database_url
from app.day_two import create_app
from app.privacy.entities import EntityHasher
from conftest import TEST_HASH_KEY, make_settings


def test_defaults_when_env_empty(monkeypatch):
    for name in ("ALLOWED_ORIGINS", "DATABASE_URL", "APP_VERSION", "GIT_SHA", "RATE_LIMIT_ANALYZE_PER_MIN",
                 "ENTITY_HASH_KEY"):
        monkeypatch.setenv(name, "")  # dòng `KEY=` trong .env coi như chưa đặt
    settings = load_settings()
    assert settings.allowed_origins == DEFAULT_ORIGINS and "http://localhost:3000" in settings.allowed_origins
    assert settings.database_url.startswith("sqlite:///") and settings.rate_limit_analyze == 20
    assert settings.entity_hash_key is None  # không có khóa mặc định trong code


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.vn/, https://b.vn")
    monkeypatch.setenv("RATE_LIMIT_ANALYZE_PER_MIN", "7")
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    monkeypatch.setenv("GIT_SHA", "deadbeef")
    settings = load_settings()
    assert settings.allowed_origins == ("https://a.vn", "https://b.vn")
    assert (settings.rate_limit_analyze, settings.trusted_proxy_count, settings.app_version) == (7, 1, "deadbeef")


@pytest.mark.parametrize("name,value", [("RATE_LIMIT_ANALYZE_PER_MIN", "abc"), ("RATE_LIMIT_DEFAULT_PER_MIN", "0")])
def test_bad_numbers_fail_fast(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        load_settings()


def test_postgres_scheme_is_normalized():
    assert normalize_database_url("postgres://u:p@h:5432/db") == "postgresql://u:p@h:5432/db"
    assert normalize_database_url("postgresql://u:p@h/db") == "postgresql://u:p@h/db"
    assert normalize_database_url("sqlite:///x.db") == "sqlite:///x.db"


def test_database_url_env_selects_the_database_and_creates_tables(monkeypatch, tmp_path):
    db_file = tmp_path / "nested" / "from_env.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv("ENTITY_HASH_KEY", TEST_HASH_KEY)
    app = create_app(load_settings())
    assert db_file.exists()
    assert set(inspect(app.state.engine).get_table_names()) == {"entities", "reports", "report_entities"}
    assert make_url(str(app.state.engine.url)).database == db_file.as_posix()


def test_unique_entity_constraint_and_foreign_keys_enforced(tmp_path):
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session
    from app.db.base import init_db
    from app.db.models import Entity, ReportEntity

    engine = make_engine(f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    init_db(engine)
    with Session(engine) as session:
        session.add(Entity(type="PHONE", value_hash="abc", display="x"))
        session.commit()
        session.add(Entity(type="PHONE", value_hash="abc", display="y"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        import uuid
        session.add(ReportEntity(report_id=uuid.uuid4(), entity_id=uuid.uuid4()))
        with pytest.raises(IntegrityError):  # PRAGMA foreign_keys=ON có hiệu lực
            session.commit()


@pytest.mark.parametrize("key", [None, "", "qua-ngan"])
def test_missing_or_short_hash_key_fails_at_startup_before_touching_db(tmp_path, key):
    settings = make_settings(tmp_path, entity_hash_key=key)
    with pytest.raises(ValueError, match="ENTITY_HASH_KEY"):
        create_app(settings)
    assert not (tmp_path / "test.db").exists()  # chưa tạo DB nào khi thiếu khóa


def test_hash_key_is_read_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ENTITY_HASH_KEY", TEST_HASH_KEY)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'k.db').as_posix()}")
    app = create_app(load_settings())
    assert app.state.entity_hasher.hash("PHONE", "0912345678") == EntityHasher(TEST_HASH_KEY).hash("PHONE", "0912345678")


def test_missing_schema_file_fails_at_startup(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_app(make_settings(tmp_path, schema_path=tmp_path / "khong-co.json"))
