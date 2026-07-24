"""Persistence interfaces (Layer 1).

Four logical stores, per the baseline persistence principle:
    - MetadataRepository : specs, registry, versions, run metadata (PostgreSQL)
    - ArtifactStore      : ResolvedDefinitions and execution artifacts (S3)
    - StateStore         : runtime state + resumable checkpoints (PostgreSQL)
    - (Cache is optional and introduced only where justified.)

No OpenSearch / dedicated event store / graph DB in MVP.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from eap.persistence.models import (
    Checkpoint,
    LifecycleStatus,
    ResourceRecord,
    RunRecord,
)
from eap.specifications.envelope import ResourceKind


class MetadataRepository(ABC):
    """Stores registered resources (immutable per version) and run metadata."""

    # --- resources ---
    @abstractmethod
    def put_resource(self, record: ResourceRecord) -> None:
        """Persist a new resource version. Must reject duplicate (kind,name,version)."""

    @abstractmethod
    def get_resource(self, kind: ResourceKind, name: str, version: str) -> ResourceRecord | None: ...

    @abstractmethod
    def list_versions(self, kind: ResourceKind, name: str) -> list[str]: ...

    @abstractmethod
    def list_resources(self, kind: ResourceKind | None = None) -> list[ResourceRecord]: ...

    @abstractmethod
    def set_status(
        self, kind: ResourceKind, name: str, version: str, status: LifecycleStatus
    ) -> None: ...

    @abstractmethod
    def set_alias(self, kind: ResourceKind, name: str, alias: str, version: str) -> None: ...

    @abstractmethod
    def get_alias(self, kind: ResourceKind, name: str, alias: str) -> str | None: ...

    # --- runs ---
    @abstractmethod
    def save_run(self, run: RunRecord) -> None: ...

    @abstractmethod
    def get_run(self, run_id: str) -> RunRecord | None: ...


class ArtifactStore(ABC):
    """Content-addressable / keyed blob store (ResolvedDefinitions, artifacts)."""

    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/json") -> None: ...

    @abstractmethod
    def get(self, key: str) -> bytes | None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...


class StateStore(ABC):
    """Runtime execution state + resumable checkpoints."""

    @abstractmethod
    def save_checkpoint(self, checkpoint: Checkpoint) -> None: ...

    @abstractmethod
    def load_checkpoints(self, run_id: str) -> list[Checkpoint]: ...

    @abstractmethod
    def latest_checkpoint(self, run_id: str) -> Checkpoint | None: ...
