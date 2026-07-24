"""Database adapter - transport to enterprise relational databases (stub).

Used by knowledge sources of type ``database`` or service capabilities that read
from enterprise DBs. Stubbed in MVP1; implement with psycopg / the enterprise
auth mechanism when a concrete use case requires it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from eap.adapters.base import AdapterConfig


class DatabaseAdapter(ABC):
    @abstractmethod
    def query(self, statement: str, params: dict | None = None) -> list[dict[str, Any]]: ...


class FakeDatabaseAdapter(DatabaseAdapter):
    def __init__(self, config: AdapterConfig | None = None) -> None:
        self._config = config

    def query(self, statement: str, params: dict | None = None) -> list[dict[str, Any]]:
        return [{"note": "fake-db result", "statement": statement, "params": params or {}}]


class PostgresDatabaseAdapter(DatabaseAdapter):
    def __init__(self, config: AdapterConfig) -> None:  # pragma: no cover - stub
        self._config = config

    def query(self, statement: str, params: dict | None = None):  # pragma: no cover - stub
        raise NotImplementedError("Wire psycopg here with enterprise auth.")
