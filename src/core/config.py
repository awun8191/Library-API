from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Literal


class AppSettings(BaseSettings):

    api_name: str = "Library API"
    api_version: str = "v1"
    api_description: str = "A simple library API that uses a domain driven architecture for clear separation"
    api_summary: str = "A simple library API"
    environment: Literal["development", "production"] = "development"
    database_url: str = ""
    secret_key: str = ""


    config = SettingsConfigDict(
        env_file="*.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings():
    return AppSettings()


