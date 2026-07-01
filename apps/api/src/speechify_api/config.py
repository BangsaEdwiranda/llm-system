import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./speechify.db")
    jwt_secret_key: str = os.environ.get("JWT_SECRET_KEY", "change-me-in-prod")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24


settings = Settings()
