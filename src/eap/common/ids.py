"""ID and time helpers.

Centralised so tests can monkeypatch a single source of nondeterminism.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def new_id(prefix: str = "") -> str:
    """Return a new unique id, optionally prefixed (e.g. ``run_9f2c...``)."""
    value = uuid.uuid4().hex
    return f"{prefix}_{value}" if prefix else value


def now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(UTC)


def now_iso() -> str:
    return now().isoformat()
