"""AgentSpec - an autonomous/reasoning execution entity.

    agent://auditor-report-agent/1.0.0
        model:      model://reasoning-standard/1.0.0
        skills:     [skill://auditor-extraction/2.1.0, ...]
        knowledge:  [knowledge://ratings-knowledge/2.0.0]
        guardrails: policy://auditor-guardrails/1.0.0

An Agent is distinct from a Workflow. An Agent reasons; a Workflow coordinates.
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from eap.specifications.envelope import EapResource, ResourceKind, reference_field_validator
from eap.specifications.references import Scheme


class MemoryScope(str, Enum):
    NONE = "none"
    SESSION = "session"
    LONG_TERM = "long_term"


class MemoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: MemoryScope = MemoryScope.SESSION
    max_turns: int = 20


class AgentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str  # model://...
    instructions: str | None = None
    prompt: str | None = None  # prompt://... (alternative to inline instructions)
    skills: list[str] = Field(default_factory=list)  # skill://...
    capabilities: list[str] = Field(default_factory=list)  # capability://... (direct)
    knowledge: list[str] = Field(default_factory=list)  # knowledge://...
    guardrails: str | None = None  # policy://...
    output_schema: str | None = None  # schema://...
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    max_iterations: int = 8

    @field_validator("model")
    @classmethod
    def _v_model(cls, v: str) -> str:
        return reference_field_validator(Scheme.MODEL)(v)

    @field_validator("prompt")
    @classmethod
    def _v_prompt(cls, v: str | None) -> str | None:
        return reference_field_validator(Scheme.PROMPT)(v) if v else v

    @field_validator("guardrails")
    @classmethod
    def _v_guardrails(cls, v: str | None) -> str | None:
        return reference_field_validator(Scheme.POLICY)(v) if v else v

    @field_validator("output_schema")
    @classmethod
    def _v_schema(cls, v: str | None) -> str | None:
        return reference_field_validator(Scheme.SCHEMA)(v) if v else v

    @field_validator("skills")
    @classmethod
    def _v_skills(cls, v: list[str]) -> list[str]:
        validate = reference_field_validator(Scheme.SKILL)
        return [validate(i) for i in v]

    @field_validator("capabilities")
    @classmethod
    def _v_caps(cls, v: list[str]) -> list[str]:
        validate = reference_field_validator(Scheme.CAPABILITY)
        return [validate(i) for i in v]

    @field_validator("knowledge")
    @classmethod
    def _v_knowledge(cls, v: list[str]) -> list[str]:
        validate = reference_field_validator(Scheme.KNOWLEDGE)
        return [validate(i) for i in v]


class Agent(EapResource):
    expected_kind: ClassVar[ResourceKind] = ResourceKind.AGENT

    kind: ResourceKind = ResourceKind.AGENT
    spec: AgentSpec
