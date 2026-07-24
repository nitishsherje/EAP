"""PostgreSQL metadata/state repositories (stub).

Wiring point for the real CRISIL PostgreSQL. Intentionally a stub in MVP1: the
in-memory implementation covers the walking skeleton and tests. Implement these
against ``psycopg`` (install with the ``adapters`` extra) when persistence is
promoted. Connection settings/credentials come from the SecretsProvider, never
from source.

Suggested schema:
    resources(kind, name, version, status, body jsonb, created_at, updated_at,
              PRIMARY KEY (kind, name, version))
    resource_aliases(kind, name, alias, version, PRIMARY KEY (kind, name, alias))
    runs(id, target, environment, resolved_hash, status, request jsonb,
         result jsonb, error jsonb, created_at, updated_at)
    checkpoints(run_id, name, state jsonb, created_at)
"""

from __future__ import annotations

from eap.persistence.base import MetadataRepository, StateStore

_NOT_IMPLEMENTED = (
    "PostgreSQL persistence is not yet implemented. Set EAP_METADATA_BACKEND=memory "
    "for local/dev, or implement PostgresMetadataRepository against psycopg."
)


class PostgresMetadataRepository(MetadataRepository):
    def __init__(self, dsn: str) -> None:  # pragma: no cover - stub
        raise NotImplementedError(_NOT_IMPLEMENTED)


class PostgresStateStore(StateStore):
    def __init__(self, dsn: str) -> None:  # pragma: no cover - stub
        raise NotImplementedError(_NOT_IMPLEMENTED)
