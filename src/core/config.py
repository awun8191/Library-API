from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

API_PREFIX = "/api/v1"


class AppSettings(BaseSettings):
    api_name: str = "Library API"
    api_version: str = "v1"
    api_prefix: str = API_PREFIX
    api_description: str = "A simple library API that uses a domain driven architecture for clear separation"
    api_summary: str = "A simple library API"
    environment: Literal["development", "production"] = "development"
    database_url: str = Field(min_length=1)
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=1)
    cors_allow_origins: str = "*"
    storage_dir: str = "Storage"
    rate_limit_enabled: bool = True
    rate_limit_backend: Literal["postgres", "memory"] = "postgres"
    rate_limit_default_per_minute: int = 120
    rate_limit_login_per_minute: int = 5
    rate_limit_signup_per_hour: int = 5
    rate_limit_upload_per_hour: int = 30
    trust_proxy_headers: bool = False
    max_upload_mb: int = Field(default=4, ge=1)
    log_level: str = "INFO"
    log_json: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        """Return the allowed origins as a list."""
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> AppSettings:
    return AppSettings()
