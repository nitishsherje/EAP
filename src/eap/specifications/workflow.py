"""WorkflowSpec - coordinates agents/skills/steps to achieve a goal.

Separate from AgentSpec. Supports sequential, parallel, graph, fan-out/fan-in,
iterative and dynamic/agentic patterns. EAP governs these patterns; Microsoft
Agent Framework provides the execution primitives.

    workflow://rating-note-generation/1.0.0
"""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from eap.specifications.envelope import EapResource, ResourceKind
from eap.specifications.references import Reference, ReferenceError, Scheme


class WorkflowPattern(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    GRAPH = "graph"
    FAN_OUT_FAN_IN = "fan_out_fan_in"
    ITERATIVE = "iterative"
    DYNAMIC = "dynamic"


class StepType(str, Enum):
    AGENT = "agent"
    SKILL = "skill"
    WORKFLOW = "workflow"


_STEP_SCHEME = {
    StepType.AGENT: Scheme.AGENT,
    StepType.SKILL: Scheme.SKILL,
    StepType.WORKFLOW: Scheme.WORKFLOW,
}


class WorkflowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9_-]*$")
    type: StepType
    ref: str  # agent:// | skill:// | workflow://
    inputs: dict[str, Any] = Field(default_factory=dict)  # supports ${step.output} refs
    depends_on: list[str] = Field(default_factory=list)

    @field_validator("ref")
    @classmethod
    def _v_ref(cls, v: str, info) -> str:  # noqa: ANN001
        try:
            ref = Reference.parse(v)
        except ReferenceError as exc:
            raise ValueError(str(exc)) from exc
        step_type: StepType | None = info.data.get("type")
        if step_type is not None and ref.scheme != _STEP_SCHEME[step_type]:
            raise ValueError(
                f"step ref {v!r} scheme must match step type {step_type.value!r}"
            )
        return v


class WorkflowSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: WorkflowPattern = WorkflowPattern.SEQUENTIAL
    steps: list[WorkflowStep] = Field(..., min_length=1)
    output_targets: list[str] = Field(default_factory=list)  # step ids to emit
    on_error: str = "fail"  # fail | continue | compensate

    @field_validator("steps")
    @classmethod
    def _v_unique_ids(cls, v: list[WorkflowStep]) -> list[WorkflowStep]:
        ids = [s.id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("workflow step ids must be unique")
        return v


class Workflow(EapResource):
    expected_kind: ClassVar[ResourceKind] = ResourceKind.WORKFLOW

    kind: ResourceKind = ResourceKind.WORKFLOW
    spec: WorkflowSpec
