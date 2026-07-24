"""Typed settings loaded from the env"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LTV_", env_file = ".env", extra = "ignore")

    database_url: str = "postgresql+psycopg://ltv:ltv@localhost:5432/ltv"
    log_level: str = "INFO"
    log_json: bool = False
    raw_path: str = "data/raw/online_retail_II.xlsx"


@lru_cache
def get_settings() -> Settings:
    return Settings()