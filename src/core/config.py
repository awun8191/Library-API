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
