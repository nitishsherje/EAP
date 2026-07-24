"""Policy - governed access / guardrail rules.

Referenced as ``policy://<name>/<version>``. A policy is a set of statements the
Governance service evaluates (RBAC/ABAC style) plus optional guardrail and data
classification directives applied during resolution and execution.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from eap.specifications.envelope import EapResource, ResourceKind


class Effect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class PolicyStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    effect: Effect
    actions: list[str] = Field(default_factory=list)  # e.g. ["run", "resolve"]
    resources: list[str] = Field(default_factory=list)  # ref patterns, e.g. "agent://*"
    # ABAC conditions, e.g. {"data_classification": "internal"}.
    conditions: dict[str, Any] = Field(default_factory=dict)


class GuardrailRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str  # e.g. "content_safety", "pii", "prompt_injection"
    action: str = "block"  # block | redact | warn
    config: dict[str, Any] = Field(default_factory=dict)


class PolicySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statements: list[PolicyStatement] = Field(default_factory=list)
    guardrails: list[GuardrailRule] = Field(default_factory=list)
    data_classification: str = "internal"  # public | internal | confidential | restricted


class Policy(EapResource):
    expected_kind: ClassVar[ResourceKind] = ResourceKind.POLICY

    kind: ResourceKind = ResourceKind.POLICY
    spec: PolicySpec
