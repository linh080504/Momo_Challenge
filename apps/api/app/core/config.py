"""Cấu hình API — chỉ đọc từ biến môi trường. Không có secret mặc định nào trong code."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from app import __version__

API_ROOT = Path(__file__).resolve().parents[2]  # apps/api
REPO_ROOT = Path(__file__).resolve().parents[4]  # gốc repo (chứa .claude/skills)

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB byte gốc — khớp DECISIONS 2026-11-24 và run_eval.py
DEFAULT_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
DEFAULT_SCHEMA_PATH = REPO_ROOT / ".claude" / "skills" / "scam-analyzer" / "analysis.schema.json"
DEFAULT_VIETQR_PATH = REPO_ROOT / ".claude" / "skills" / "vietqr" / "scripts" / "vietqr.py"
DEFAULT_DATABASE_URL = f"sqlite:///{(API_ROOT / 'data' / 'tkc.db').as_posix()}"


def _env(name: str) -> str | None:
    """Giá trị biến môi trường; chuỗi rỗng (dòng `KEY=` trong .env) coi như chưa đặt."""
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _env_number(name: str, default, cast, minimum):
    raw = _env(name)
    if raw is None:
        return default
    try:
        value = cast(raw)
    except ValueError:
        raise ValueError(f"Biến môi trường {name} phải là số (nhận {raw!r})") from None
    if value < minimum:
        raise ValueError(f"Biến môi trường {name} phải >= {minimum} (nhận {value})")
    return value


@dataclass(frozen=True)
class Settings:
    app_version: str = __version__
    database_url: str = DEFAULT_DATABASE_URL
    allowed_origins: tuple[str, ...] = DEFAULT_ORIGINS

    # Giới hạn đầu vào
    max_image_bytes: int = MAX_IMAGE_BYTES
    max_body_bytes: int = 8 * 1024 * 1024  # 5 MB ảnh -> ~6,7 MB base64 + văn bản + JSON
    max_text_chars: int = 10_000

    analyze_timeout_s: float = 25.0

    # Rate limit theo IP (số request / cửa sổ). Theo tài khoản: làm cùng đăng nhập (ngày 5).
    rate_limit_window_s: float = 60.0
    rate_limit_analyze: int = 20
    rate_limit_reports: int = 10
    rate_limit_default: int = 60
    trusted_proxy_count: int = 0  # số proxy tin cậy đứng trước API (đọc X-Forwarded-For từ phải sang)

    content_retention_days: int = 30  # pii-guard: nội dung đóng góp lưu tối đa 30 ngày

    # Khóa HMAC cho hash thực thể. repr=False: Settings hay bị in ra trong log/traceback/test, khóa không được lộ.
    entity_hash_key: str | None = field(default=None, repr=False)

    schema_path: Path = DEFAULT_SCHEMA_PATH
    vietqr_path: Path = DEFAULT_VIETQR_PATH


def load_settings() -> Settings:
    origins = _env("ALLOWED_ORIGINS")
    return Settings(
        app_version=_env("APP_VERSION") or _env("GIT_SHA") or __version__,
        database_url=_env("DATABASE_URL") or DEFAULT_DATABASE_URL,
        allowed_origins=tuple(o.strip().rstrip("/") for o in origins.split(",") if o.strip())
        if origins else DEFAULT_ORIGINS,
        analyze_timeout_s=_env_number("ANALYZE_TIMEOUT_SECONDS", 25.0, float, 1),
        rate_limit_analyze=_env_number("RATE_LIMIT_ANALYZE_PER_MIN", 20, int, 1),
        rate_limit_reports=_env_number("RATE_LIMIT_REPORTS_PER_MIN", 10, int, 1),
        rate_limit_default=_env_number("RATE_LIMIT_DEFAULT_PER_MIN", 60, int, 1),
        trusted_proxy_count=_env_number("TRUSTED_PROXY_COUNT", 0, int, 0),
        entity_hash_key=_env("ENTITY_HASH_KEY"),
        schema_path=Path(_env("ANALYSIS_SCHEMA_PATH") or DEFAULT_SCHEMA_PATH),
        vietqr_path=Path(_env("VIETQR_SCRIPT_PATH") or DEFAULT_VIETQR_PATH),
    )
