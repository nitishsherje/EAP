"""Persistence layer (Layer 1): repositories + backend factory."""

from __future__ import annotations

from eap.common.config import Settings
from eap.persistence.base import ArtifactStore, MetadataRepository, StateStore
from eap.persistence.memory import (
    InMemoryArtifactStore,
    InMemoryMetadataRepository,
    InMemoryStateStore,
)
from eap.persistence.models import (
    Checkpoint,
    LifecycleStatus,
    ResourceRecord,
    RunRecord,
    RunStatus,
)


def build_metadata_repository(settings: Settings) -> MetadataRepository:
    if settings.metadata_backend == "postgres":
        from eap.persistence.postgres import PostgresMetadataRepository

        return PostgresMetadataRepository(dsn="")  # type: ignore[abstract]  # stub
    return InMemoryMetadataRepository()


def build_artifact_store(settings: Settings) -> ArtifactStore:
    if settings.artifact_backend == "s3":
        from eap.persistence.s3 import S3ArtifactStore

        return S3ArtifactStore(bucket="")  # type: ignore[abstract]  # stub
    return InMemoryArtifactStore()


def build_state_store(settings: Settings) -> StateStore:
    if settings.metadata_backend == "postgres":
        from eap.persistence.postgres import PostgresStateStore

        return PostgresStateStore(dsn="")  # type: ignore[abstract]  # stub
    return InMemoryStateStore()


__all__ = [
    "ArtifactStore",
    "Checkpoint",
    "InMemoryArtifactStore",
    "InMemoryMetadataRepository",
    "InMemoryStateStore",
    "LifecycleStatus",
    "MetadataRepository",
    "ResourceRecord",
    "RunRecord",
    "RunStatus",
    "StateStore",
    "build_artifact_store",
    "build_metadata_repository",
    "build_state_store",
]
