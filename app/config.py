"""Settings, loaded from the environment.

Everything that differs between a laptop, CI and production lives here and
nowhere else. No module reads os.environ directly.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://nutrition:nutrition@localhost:5432/nutrition"
    jwt_secret: str = "dev-only-do-not-use-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is read once per process, not per request."""
    return Settings()
