"""Settings, loaded from the environment.

Everything that differs between a laptop, CI and production lives here and
nowhere else. No module reads os.environ directly.
"""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-do-not-use-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://nutrition:nutrition@localhost:5432/nutrition"
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    # Comma-separated origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _refuse_default_secret_in_production(self) -> "Settings":
        # A deployment that forgot to set JWT_SECRET would sign every token with a
        # value that is public in this repository. Fail at boot instead.
        if self.environment == "production" and self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set when ENVIRONMENT=production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is read once per process, not per request."""
    return Settings()
