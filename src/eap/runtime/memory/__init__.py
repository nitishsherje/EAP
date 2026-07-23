"""MemoryService - short-term (session) conversation memory.

MVP1 implements session-scoped memory in-process. Long-term memory can plug in
behind the same interface (backed by a store) when a use case requires it.
"""

from __future__ import annotations

from collections import defaultdict

from eap.adapters import Message
from eap.specifications.agent import MemoryScope


class MemoryService:
    def __init__(self) -> None:
        self._sessions: dict[str, list[Message]] = defaultdict(list)

    def history(self, session_id: str, scope: MemoryScope, max_turns: int) -> list[Message]:
        if scope == MemoryScope.NONE:
            return []
        return self._sessions.get(session_id, [])[-max_turns * 2:]

    def append(self, session_id: str, message: Message) -> None:
        self._sessions[session_id].append(message)

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
