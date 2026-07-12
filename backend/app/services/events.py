"""In-process async event bus backing the SSE ``/environmental/events`` stream.

Publishers push domain events (``carbon.created`` from the carbon flow here,
``score.updated`` from the scoring zone) and every connected SSE subscriber
receives them. Intentionally in-memory and single-process — perfect for the
local/dev deployment; a multi-process deployment would swap this for Redis
pub/sub behind the same ``publish`` / ``subscribe`` API.

Publishing is thread-safe: sync request handlers run in Starlette's threadpool,
so events are handed to the event loop via ``call_soon_threadsafe`` rather than
touching the (not thread-safe) ``asyncio.Queue`` directly.
"""

from __future__ import annotations

import asyncio
from typing import Any

CARBON_CREATED = "carbon.created"
SCORE_UPDATED = "score.updated"

_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
_loop: asyncio.AbstractEventLoop | None = None


def bind_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Remember the running event loop so cross-thread publishes can reach it."""
    global _loop
    _loop = loop


async def subscribe() -> asyncio.Queue[dict[str, Any]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue[dict[str, Any]]) -> None:
    _subscribers.discard(q)


def publish(event: str, data: dict[str, Any]) -> None:
    """Fan a message out to every subscriber, safe to call from any thread."""
    message = {"event": event, "data": data}
    for q in list(_subscribers):
        if _loop is not None and _loop.is_running():
            _loop.call_soon_threadsafe(q.put_nowait, message)
        else:
            # No loop bound yet (no SSE client has ever connected); best effort.
            q.put_nowait(message)


def publish_carbon_created(data: dict[str, Any]) -> None:
    publish(CARBON_CREATED, data)


def publish_score_updated(data: dict[str, Any]) -> None:
    publish(SCORE_UPDATED, data)
