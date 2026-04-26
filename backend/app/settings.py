"""Pydantic-settings configuration for BAI Core Trader backend."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from platformdirs import user_data_dir, user_log_dir
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


APP_NAME = "BaiCoreTrader"
APP_AUTHOR = "BAI Core"


def _data_root() -> Path:
    return Path(user_data_dir(APP_NAME, APP_AUTHOR, roaming=True))


def _logs_root() -> Path:
    return Path(user_log_dir(APP_NAME, APP_AUTHOR))


class Settings(BaseSettings):
    """Runtime settings, overridable via env vars (BCT_*) or .env."""

    model_config = SettingsConfigDict(
        env_prefix="BCT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="127.0.0.1", description="Bind address — always loopback in production")
    port: int = Field(default=0, description="0 = ephemeral, set by desktop launcher")
    log_level: str = Field(default="INFO")

    ngrok_authtoken: str | None = Field(default=None, description="Optional pyngrok auth token")
    locale: str = Field(default="ru")

    data_dir: Path = Field(default_factory=_data_root)
    logs_dir: Path = Field(default_factory=_logs_root)

    cors_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:*", "http://localhost:*"])

    jwt_ttl_minutes: int = Field(default=24 * 60)
    auth_lockout_attempts: int = Field(default=3)
    auth_lockout_minutes: int = Field(default=10)

    static_dir: Path | None = Field(default=None, description="Path to built frontend dist")

    dev_mode: bool = Field(default=False)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def vault_path(self) -> Path:
        return self.data_dir / "credentials.enc"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "data_cache"

    @property
    def log_file(self) -> Path:
        return self.logs_dir / "bot.log"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.logs_dir, self.cache_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
