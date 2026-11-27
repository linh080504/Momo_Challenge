from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_version: str = "0.1.0"
    database_url: str = "sqlite:///./tkc.sqlite3"
    app_secret: str = ""
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    demo_user_email: str = ""
    demo_user_password: str = ""
    demo_ops_email: str = ""
    demo_ops_password: str = ""
    ocr_command: str = ""
    ocr_languages: str = "vie+eng"
    whisper_command: str = ""
    whisper_model_path: str = ""
    node_command: str = "node"
    dashscope_api_key: SecretStr = SecretStr("")
    safe_browsing_key: str = ""
    virustotal_api_key: SecretStr = SecretStr("")
    urlhaus_feed_path: str = ""
    phishtank_feed_path: str = ""
    website_capture_enabled: bool = False
    website_public_html_enabled: bool = False
    rdap_lookups_per_hour: int = Field(0, ge=0, le=30)
    fraud_url_model_path: str = ""
    analysis_per_minute: int = Field(30, gt=0)
    demo_analysis_per_minute: int = Field(120, gt=0)
    reports_per_minute: int = Field(12, gt=0, le=120)
    llm_calls_per_day: int = Field(300, ge=0)
