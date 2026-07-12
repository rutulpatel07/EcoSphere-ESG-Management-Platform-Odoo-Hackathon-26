"""Application configuration read from environment variables.

``.env`` (if present) is loaded first via python-dotenv so local development
picks up secrets/DB settings without exporting them by hand. Required secrets
have no insecure fallback: a missing ``JWT_SECRET`` fails fast at import time.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    """Return a required environment variable or raise a clear startup error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable {name} is not set. "
            "Copy backend/.env.example to backend/.env and fill it in."
        )
    return value


class Settings:
    """Runtime settings sourced from the environment (local Postgres only)."""

    APP_NAME: str = "EcoSphere ESG Management Platform"
    API_PREFIX: str = "/api"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://ecosphere:ecosphere@localhost:5432/ecosphere_db",
    )

    # No insecure default: a missing JWT_SECRET raises at startup rather than
    # silently signing tokens with a well-known key.
    JWT_SECRET: str = _require("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))

    # Comma-separated list of allowed CORS origins (Vite dev server by default).
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")


settings = Settings()
