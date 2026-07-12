"""FastAPI application factory for the EcoSphere ESG Management Platform.

All routers are registered here at import time so the full API surface is
mounted under ``/api``. Individual routers currently expose a single
``GET /ping`` stub; business logic is filled in per owner zone.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    auth,
    carbon,
    dashboard,
    departments,
    environmental,
    gamification,
    governance,
    ledger,
    notifications,
    operations,
    reports,
    social,
    users,
)
from app.routers import settings as settings_router

# Every router in the owner-zone map, registered now.
ALL_ROUTERS = (
    auth.router,
    users.router,
    departments.router,
    dashboard.router,
    environmental.router,
    operations.router,
    carbon.router,
    social.router,
    governance.router,
    ledger.router,
    gamification.router,
    reports.router,
    settings_router.router,
    notifications.router,
)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "app": settings.APP_NAME}

    for router in ALL_ROUTERS:
        app.include_router(router, prefix=settings.API_PREFIX)

    return app


app = create_app()
