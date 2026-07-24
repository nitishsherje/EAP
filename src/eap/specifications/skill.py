"""SkillSpec - a reusable business ability.

A Skill is NOT a tool. It is a reusable business ability that may be
deterministic, agentic, or function-based, and which *uses* capabilities,
knowledge, prompts and models to do its job.

    skill://auditor-extraction/2.1.0
        capabilities: [capability://document-intelligence/1.0.0]
        knowledge:    [knowledge://ratings-knowledge/2.0.0]
"""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from eap.specifications.envelope import EapResource, ResourceKind, reference_field_validator
from eap.specifications.references import Scheme


class SkillType(str, Enum):
    DETERMINISTIC = "deterministic"
    AGENTIC = "agentic"
    FUNCTION = "function"


class CapabilityUse(BaseModel):
    """A capability the skill depends on, and (optionally) the operation used."""

    model_config = ConfigDict(extra="forbid")

    ref: str  # capability://...
    operation: str | None = None

    _validate_ref = field_validator("ref")(reference_field_validator(Scheme.CAPABILITY))


class SkillSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: SkillType = SkillType.DETERMINISTIC
    description: str = ""
    instructions: str | None = None  # for agentic/function skills
    prompt: str | None = None  # prompt://...
    model: str | None = None  # model://... (agentic skills)
    capabilities: list[CapabilityUse] = Field(default_factory=list)
    knowledge: list[str] = Field(default_factory=list)  # knowledge://...
    inputs: dict[str, Any] = Field(default_factory=dict)  # JSON-schema-ish
    outputs: dict[str, Any] = Field(default_factory=dict)
    output_schema: str | None = None  # schema://...

    @field_validator("prompt")
    @classmethod
    def _v_prompt(cls, v: str | None) -> str | None:
        return reference_field_validator(Scheme.PROMPT)(v) if v else v

    @field_validator("model")
    @classmethod
    def _v_model(cls, v: str | None) -> str | None:
        return reference_field_validator(Scheme.MODEL)(v) if v else v

    @field_validator("output_schema")
    @classmethod
    def _v_schema(cls, v: str | None) -> str | None:
        return reference_field_validator(Scheme.SCHEMA)(v) if v else v

    @field_validator("knowledge")
    @classmethod
    def _v_knowledge(cls, v: list[str]) -> list[str]:
        validate = reference_field_validator(Scheme.KNOWLEDGE)
        return [validate(item) for item in v]


class Skill(EapResource):
    expected_kind: ClassVar[ResourceKind] = ResourceKind.SKILL

    kind: ResourceKind = ResourceKind.SKILL
    spec: SkillSpec
