"""In-memory persistence implementations.

Default backend for local development, tests and the walking skeleton. Swap for
PostgreSQL/S3 via configuration without touching any caller.
"""

from __future__ import annotations

from eap.common.errors import AlreadyExistsError
from eap.persistence.base import ArtifactStore, MetadataRepository, StateStore
from eap.persistence.models import (
    Checkpoint,
    LifecycleStatus,
    ResourceRecord,
    RunRecord,
)
from eap.specifications.envelope import ResourceKind


class InMemoryMetadataRepository(MetadataRepository):
    def __init__(self) -> None:
        self._resources: dict[str, ResourceRecord] = {}
        self._aliases: dict[str, str] = {}  # "kind:name:alias" -> version
        self._runs: dict[str, RunRecord] = {}

    @staticmethod
    def _rkey(kind: ResourceKind, name: str, version: str) -> str:
        return f"{kind.value}:{name}:{version}"

    def put_resource(self, record: ResourceRecord) -> None:
        key = self._rkey(record.kind, record.name, record.version)
        if key in self._resources:
            raise AlreadyExistsError(f"{key} already registered (versions are immutable)")
        self._resources[key] = record

    def get_resource(self, kind: ResourceKind, name: str, version: str) -> ResourceRecord | None:
        return self._resources.get(self._rkey(kind, name, version))

    def list_versions(self, kind: ResourceKind, name: str) -> list[str]:
        prefix = f"{kind.value}:{name}:"
        return [k[len(prefix):] for k in self._resources if k.startswith(prefix)]

    def list_resources(self, kind: ResourceKind | None = None) -> list[ResourceRecord]:
        records = list(self._resources.values())
        if kind is not None:
            records = [r for r in records if r.kind == kind]
        return records

    def set_status(
        self, kind: ResourceKind, name: str, version: str, status: LifecycleStatus
    ) -> None:
        record = self.get_resource(kind, name, version)
        if record is None:
            from eap.common.errors import NotFoundError

            raise NotFoundError(f"{self._rkey(kind, name, version)} not found")
        record.status = status

    def set_alias(self, kind: ResourceKind, name: str, alias: str, version: str) -> None:
        self._aliases[f"{kind.value}:{name}:{alias}"] = version

    def get_alias(self, kind: ResourceKind, name: str, alias: str) -> str | None:
        return self._aliases.get(f"{kind.value}:{name}:{alias}")

    def save_run(self, run: RunRecord) -> None:
        self._runs[run.id] = run

    def get_run(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)


class InMemoryArtifactStore(ArtifactStore):
    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str = "application/json") -> None:
        self._blobs[key] = data

    def get(self, key: str) -> bytes | None:
        return self._blobs.get(key)

    def exists(self, key: str) -> bool:
        return key in self._blobs


class InMemoryStateStore(StateStore):
    def __init__(self) -> None:
        self._checkpoints: dict[str, list[Checkpoint]] = {}

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        self._checkpoints.setdefault(checkpoint.run_id, []).append(checkpoint)

    def load_checkpoints(self, run_id: str) -> list[Checkpoint]:
        return list(self._checkpoints.get(run_id, []))

    def latest_checkpoint(self, run_id: str) -> Checkpoint | None:
        items = self._checkpoints.get(run_id)
        return items[-1] if items else None
