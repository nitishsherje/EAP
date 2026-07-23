"""Persistence-facing records (not authoring specs)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eap.common.ids import new_id, now_iso
from eap.specifications.envelope import EapResource, ResourceKind


class LifecycleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class ResourceRecord(BaseModel):
    """A registered resource plus its lifecycle metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: ResourceKind
    name: str
    version: str
    resource: EapResource
    status: LifecycleStatus = LifecycleStatus.DRAFT
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

    @property
    def key(self) -> str:
        return f"{self.kind.value}:{self.name}:{self.version}"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_HITL = "waiting_hitl"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunRecord(BaseModel):
    """Execution metadata for a single run (agent or workflow)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("run"))
    target: str = ""
    environment: str = "dev"
    resolved_hash: str = ""
    status: RunStatus = RunStatus.PENDING
    request: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class Checkpoint(BaseModel):
    """A resumable execution checkpoint."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    name: str
    state: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)
