"""State & Checkpoint Service - resumable execution state.

Wraps the StateStore so strategies can checkpoint progress and resume after a
failure or a human-in-the-loop pause.
"""

from __future__ import annotations

from typing import Any

from eap.persistence.base import StateStore
from eap.persistence.models import Checkpoint


class StateCheckpointService:
    def __init__(self, store: StateStore) -> None:
        self._store = store

    def checkpoint(self, run_id: str, name: str, state: dict[str, Any]) -> None:
        self._store.save_checkpoint(Checkpoint(run_id=run_id, name=name, state=state))

    def latest(self, run_id: str) -> Checkpoint | None:
        return self._store.latest_checkpoint(run_id)

    def get(self, run_id: str, name: str) -> Checkpoint | None:
        for cp in self._store.load_checkpoints(run_id):
            if cp.name == name:
                return cp
        return None
