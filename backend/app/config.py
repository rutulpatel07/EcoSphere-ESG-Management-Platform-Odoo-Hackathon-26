"""Application configuration read from environment variables."""

import os


class Settings:
    """Runtime settings sourced from the environment (local Postgres only)."""

    APP_NAME: str = "EcoSphere ESG Management Platform"
    API_PREFIX: str = "/api"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://ecosphere:ecosphere@localhost:5432/ecosphere",
    )

    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))

    # Comma-separated list of allowed CORS origins (Vite dev server by default).
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")


settings = Settings()
