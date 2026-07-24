"""Canonical resource envelope shared by every specification kind.

    apiVersion: eap.crisil/v1
    kind: <ResourceKind>
    metadata:
      name / version / description / domain / owner
    spec:
      ...
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from eap.specifications.references import Reference, ReferenceError, Scheme
from eap.specifications.versioning import SemVer

API_VERSION = "eap.crisil/v1"


class ResourceKind(str, Enum):
    AGENT = "Agent"
    WORKFLOW = "Workflow"
    SKILL = "Skill"
    CAPABILITY = "Capability"
    KNOWLEDGE = "Knowledge"
    MODEL_PROFILE = "ModelProfile"
    PROMPT = "Prompt"
    POLICY = "Policy"
    OUTPUT_SCHEMA = "OutputSchema"
    CAPABILITY_BINDING = "CapabilityBinding"
    RESOLVED_DEFINITION = "ResolvedDefinition"


# Kinds that live in the registry and are referenceable/versioned by authors.
REGISTRABLE_KINDS = frozenset(
    {
        ResourceKind.AGENT,
        ResourceKind.WORKFLOW,
        ResourceKind.SKILL,
        ResourceKind.CAPABILITY,
        ResourceKind.KNOWLEDGE,
        ResourceKind.MODEL_PROFILE,
        ResourceKind.PROMPT,
        ResourceKind.POLICY,
        ResourceKind.OUTPUT_SCHEMA,
    }
)


class Metadata(BaseModel):
    """Common identity/governance metadata for every resource."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9._-]*$")
    version: str = Field(..., description="Semantic version MAJOR.MINOR.PATCH")
    description: str = ""
    domain: str = ""
    owner: str = ""
    labels: dict[str, str] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list, description="e.g. ['stable']")

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: str) -> str:
        if not SemVer.is_valid(v):
            raise ValueError(f"metadata.version must be MAJOR.MINOR.PATCH, got {v!r}")
        return v

    @property
    def semver(self) -> SemVer:
        return SemVer.parse(self.version)


class EapResource(BaseModel):
    """Base class for all authored specifications."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    expected_kind: ClassVar[ResourceKind | None] = None

    api_version: str = Field(default=API_VERSION, alias="apiVersion")
    kind: ResourceKind
    metadata: Metadata

    @field_validator("api_version")
    @classmethod
    def _validate_api_version(cls, v: str) -> str:
        if v != API_VERSION:
            raise ValueError(f"Unsupported apiVersion {v!r}; expected {API_VERSION!r}")
        return v

    @model_validator(mode="after")
    def _validate_kind(self) -> EapResource:
        if self.expected_kind is not None and self.kind != self.expected_kind:
            raise ValueError(
                f"kind mismatch: expected {self.expected_kind.value!r}, got {self.kind.value!r}"
            )
        return self

    @property
    def ref(self) -> Reference:
        """The logical, pinned reference identifying this exact resource version."""
        scheme = _KIND_TO_SCHEME[self.kind]
        return Reference(scheme=scheme, name=self.metadata.name, version=self.metadata.version)

    @property
    def key(self) -> str:
        """Registry key: ``kind:name:version``."""
        return f"{self.kind.value}:{self.metadata.name}:{self.metadata.version}"


_KIND_TO_SCHEME: dict[ResourceKind, Scheme] = {
    ResourceKind.AGENT: Scheme.AGENT,
    ResourceKind.WORKFLOW: Scheme.WORKFLOW,
    ResourceKind.SKILL: Scheme.SKILL,
    ResourceKind.CAPABILITY: Scheme.CAPABILITY,
    ResourceKind.KNOWLEDGE: Scheme.KNOWLEDGE,
    ResourceKind.MODEL_PROFILE: Scheme.MODEL,
    ResourceKind.PROMPT: Scheme.PROMPT,
    ResourceKind.POLICY: Scheme.POLICY,
    ResourceKind.OUTPUT_SCHEMA: Scheme.SCHEMA,
}


def reference_field_validator(*allowed: Scheme):
    """Build a reusable pydantic validator that checks reference strings.

    Usage inside a model::

        _v = field_validator("model")(reference_field_validator(Scheme.MODEL))
    """

    allowed_set = set(allowed)

    def _validate(value: str) -> str:
        try:
            ref = Reference.parse(value)
        except ReferenceError as exc:
            raise ValueError(str(exc)) from exc
        if allowed_set and ref.scheme not in allowed_set:
            names = ", ".join(s.value for s in allowed_set)
            raise ValueError(f"Reference {value!r} must use scheme(s): {names}")
        return value

    return _validate
