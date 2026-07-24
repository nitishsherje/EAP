"""Catalog - read/query views over the registry.

Provides discovery-oriented listings (by kind, domain, owner) and lightweight
summaries for UIs/APIs. Read-only; all writes go through the Registry.
"""

from __future__ import annotations

from dataclasses import dataclass

from eap.control_plane.registry import Registry
from eap.persistence.models import LifecycleStatus
from eap.specifications.envelope import ResourceKind


@dataclass(frozen=True)
class CatalogEntry:
    kind: str
    name: str
    version: str
    domain: str
    owner: str
    status: str
    description: str


class Catalog:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    def list(
        self,
        kind: ResourceKind | None = None,
        domain: str | None = None,
        status: LifecycleStatus | None = None,
    ) -> list[CatalogEntry]:
        entries: list[CatalogEntry] = []
        for record in self._registry.list(kind):
            meta = record.resource.metadata
            if domain is not None and meta.domain != domain:
                continue
            if status is not None and record.status != status:
                continue
            entries.append(
                CatalogEntry(
                    kind=record.kind.value,
                    name=record.name,
                    version=record.version,
                    domain=meta.domain,
                    owner=meta.owner,
                    status=record.status.value,
                    description=meta.description,
                )
            )
        return sorted(entries, key=lambda e: (e.kind, e.name, e.version))
