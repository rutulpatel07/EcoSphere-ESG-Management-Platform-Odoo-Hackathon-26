"""In-memory generated-report history.

backend/db/schema.sql has no table for report-generation metadata, and it
is outside this owner zone. Per product decision, history is tracked as an
in-process list rather than invented as a schema table — it resets on
restart and is not shared across multiple uvicorn workers.
"""

import itertools
from datetime import datetime, timezone

_next_id = itertools.count(5001)
_history: list[dict] = []


def record(*, name: str, format: str, size_bytes: int) -> dict:
    entry = {
        "id": next(_next_id),
        "name": name,
        "format": format,
        "generated_at": datetime.now(timezone.utc),
        "size_kb": round(size_bytes / 1024, 1),
    }
    _history.append(entry)
    return entry


def recent(limit: int = 50) -> list[dict]:
    return list(reversed(_history[-limit:]))
