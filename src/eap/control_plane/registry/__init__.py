"""Registry - stores versioned resources and resolves references to versions.

Backed by the MetadataRepository. Versions are immutable once registered. The
registry knows how to turn a (possibly unpinned/alias/partial) reference into a
concrete, published resource version.
"""

from __future__ import annotations

from eap.common.errors import NotFoundError
from eap.persistence.base import MetadataRepository
from eap.persistence.models import LifecycleStatus, ResourceRecord
from eap.specifications.envelope import EapResource, ResourceKind
from eap.specifications.references import SCHEME_KINDS, Reference
from eap.specifications.versioning import SemVer, select_version


class Registry:
    def __init__(self, repo: MetadataRepository) -> None:
        self._repo = repo

    def register(
        self, resource: EapResource, status: LifecycleStatus = LifecycleStatus.DRAFT
    ) -> ResourceRecord:
        record = ResourceRecord(
            kind=resource.kind,
            name=resource.metadata.name,
            version=resource.metadata.version,
            resource=resource,
            status=status,
        )
        self._repo.put_resource(record)
        for alias in resource.metadata.aliases:
            self._repo.set_alias(resource.kind, resource.metadata.name, alias, resource.metadata.version)
        return record

    def get(self, kind: ResourceKind, name: str, version: str) -> EapResource | None:
        record = self._repo.get_resource(kind, name, version)
        return record.resource if record else None

    def get_record(self, kind: ResourceKind, name: str, version: str) -> ResourceRecord | None:
        return self._repo.get_resource(kind, name, version)

    def list_versions(self, kind: ResourceKind, name: str) -> list[SemVer]:
        return sorted(
            (SemVer.parse(v) for v in self._repo.list_versions(kind, name)),
            reverse=True,
        )

    def list(self, kind: ResourceKind | None = None) -> list[ResourceRecord]:
        return self._repo.list_resources(kind)

    def resolve(self, ref: Reference, *, published_only: bool = True) -> ResourceRecord:
        """Resolve a reference to a concrete resource record (pinned version)."""
        kind = ResourceKind(SCHEME_KINDS[ref.scheme])

        # Alias resolution (e.g. "stable").
        version = ref.version
        if version is not None and not SemVer.is_valid(version):
            alias_version = self._repo.get_alias(kind, ref.name, version)
            if alias_version is not None:
                version = alias_version

        available = self.list_versions(kind, ref.name)
        if published_only:
            available = [
                v
                for v in available
                if self._is_published(kind, ref.name, str(v))
            ]
        selected = select_version(available, version)
        if selected is None:
            raise NotFoundError(
                f"Cannot resolve {ref}: no matching "
                f"{'published ' if published_only else ''}version "
                f"(available: {[str(v) for v in available]})"
            )
        record = self._repo.get_resource(kind, ref.name, str(selected))
        if record is None:  # pragma: no cover - defensive
            raise NotFoundError(f"Resource {ref} disappeared during resolution")
        return record

    def _is_published(self, kind: ResourceKind, name: str, version: str) -> bool:
        record = self._repo.get_resource(kind, name, version)
        return record is not None and record.status == LifecycleStatus.PUBLISHED
