"""ResolvedDefinition - the immutable execution artifact.

This is the single most important architectural boundary in EAP. Authoring specs
may contain logical references, aliases and partial versions. Before ANYTHING
executes, the Control Plane produces a ResolvedDefinition that is:

    - Immutable        (frozen model)
    - Version pinned   (every ref resolved to exact MAJOR.MINOR.PATCH)
    - Policy validated  (effective policy captured)
    - Environment bound (bindings inlined for the target environment)
    - Integrity hashed  (content_hash over the canonical bundle)
    - Auditable         (provenance recorded)

Invariant: the Runtime executes a ResolvedDefinition, never raw mutable YAML.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eap.common.ids import new_id, now_iso
from eap.specifications.agent import Agent
from eap.specifications.binding import CapabilityBinding
from eap.specifications.capability import Capability
from eap.specifications.envelope import ResourceKind
from eap.specifications.knowledge import Knowledge
from eap.specifications.model_profile import ModelProfile
from eap.specifications.output_schema import OutputSchema
from eap.specifications.prompt import Prompt
from eap.specifications.skill import Skill
from eap.specifications.workflow import Workflow


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolver_version: str = "1.0.0"
    requested_by: str = "system"
    source_ref: str = ""  # the originally requested reference (may be unpinned)
    resolved_at: str = Field(default_factory=now_iso)


class EffectivePolicy(BaseModel):
    """Flattened policy view the runtime enforces without re-resolving policies."""

    model_config = ConfigDict(extra="forbid")

    data_classification: str = "internal"
    guardrails: list[dict[str, Any]] = Field(default_factory=list)
    required_scopes: list[str] = Field(default_factory=list)


class ResolvedBundle(BaseModel):
    """All pinned resources needed to execute the target, keyed by pinned ref."""

    model_config = ConfigDict(extra="forbid")

    agents: dict[str, Agent] = Field(default_factory=dict)
    workflows: dict[str, Workflow] = Field(default_factory=dict)
    skills: dict[str, Skill] = Field(default_factory=dict)
    capabilities: dict[str, Capability] = Field(default_factory=dict)
    knowledge: dict[str, Knowledge] = Field(default_factory=dict)
    models: dict[str, ModelProfile] = Field(default_factory=dict)
    prompts: dict[str, Prompt] = Field(default_factory=dict)
    policies: dict[str, dict[str, Any]] = Field(default_factory=dict)
    output_schemas: dict[str, OutputSchema] = Field(default_factory=dict)
    # Inlined bindings for the target environment, keyed by pinned target ref.
    bindings: dict[str, CapabilityBinding] = Field(default_factory=dict)
    # Maps every reference as-written (possibly unpinned) to its pinned ref, so the
    # runtime never has to re-resolve versions.
    resolution_map: dict[str, str] = Field(default_factory=dict)


class ResolvedDefinition(BaseModel):
    """Immutable, version-pinned, environment-bound, integrity-hashed artifact."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: new_id("rd"))
    kind: ResourceKind = ResourceKind.RESOLVED_DEFINITION
    environment: str = "dev"

    # The pinned root reference (agent://name/x.y.z or workflow://name/x.y.z).
    target: str = ""
    root_kind: ResourceKind = ResourceKind.AGENT

    bundle: ResolvedBundle = Field(default_factory=ResolvedBundle)
    effective_policy: EffectivePolicy = Field(default_factory=EffectivePolicy)
    provenance: Provenance = Field(default_factory=Provenance)

    content_hash: str = ""
    created_at: str = Field(default_factory=now_iso)

    # Fields excluded from the integrity hash (volatile / self-referential).
    _HASH_EXCLUDE = {"id", "content_hash", "created_at", "provenance"}

    def compute_hash(self) -> str:
        payload = self.model_dump(mode="json", exclude=self._HASH_EXCLUDE)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def finalize(self) -> ResolvedDefinition:
        """Return a copy with the integrity hash populated."""
        return self.model_copy(update={"content_hash": self.compute_hash()})

    def verify_integrity(self) -> bool:
        return bool(self.content_hash) and self.content_hash == self.compute_hash()

    @property
    def root_agent(self) -> Agent | None:
        return self.bundle.agents.get(self.target)

    @property
    def root_workflow(self) -> Workflow | None:
        return self.bundle.workflows.get(self.target)

    def pin(self, ref: str) -> str:
        """Map a reference as-written to its pinned form."""
        return self.bundle.resolution_map.get(ref, ref)

    def binding_for(self, ref: str) -> CapabilityBinding | None:
        return self.bundle.bindings.get(self.pin(ref))
