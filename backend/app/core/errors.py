"""Consistent JSON error envelope.

CONTRACT.md requires ``application/json`` for every response and its own error
examples (e.g. 401 ``{"detail": "Invalid credentials"}``, 409
``{"detail": "Out of stock"}``) are exactly FastAPI's default
``HTTPException``/``RequestValidationError`` shape -- so those are left
untouched; changing them would break every other zone's contract-matching
error responses.

The actual gap: an **unhandled** exception (a bug, not an intentional
``HTTPException``) currently escapes to Starlette's default handler, which
returns a plain-text/HTML 500 -- not JSON, and it leaks internals. This
registers a catch-all that normalizes only that case into the same
``{"detail": ...}`` envelope and logs the real exception server-side. It does
not shadow ``HTTPException``/``RequestValidationError``: Starlette's exception
dispatch matches the most specific registered handler by MRO, so those keep
using FastAPI's own handlers.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
