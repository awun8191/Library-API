from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    api_name: str = "Library API"
    api_version: str = "v1"
    api_description: str = "A simple library API that uses a domain driven architecture for clear separation"
    api_summary: str = "A simple library API"
    environment: Literal["development", "production"] = "development"
    database_url: str = Field(min_length=1)
    secret_key: str = Field(min_length=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> AppSettings:
    return AppSettings()
