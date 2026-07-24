"""Load and parse authoring specs (YAML / dict) into typed models.

Dispatches on ``kind`` and converts pydantic validation errors into the EAP
structured error model so every problem is reported at once with a location.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from eap.common.errors import ErrorCode, SpecValidationError, ValidationIssue
from eap.specifications.agent import Agent
from eap.specifications.binding import CapabilityBinding
from eap.specifications.capability import Capability
from eap.specifications.envelope import EapResource, ResourceKind
from eap.specifications.knowledge import Knowledge
from eap.specifications.model_profile import ModelProfile
from eap.specifications.output_schema import OutputSchema
from eap.specifications.policy import Policy
from eap.specifications.prompt import Prompt
from eap.specifications.skill import Skill
from eap.specifications.workflow import Workflow

KIND_MODELS: dict[ResourceKind, type[EapResource]] = {
    ResourceKind.AGENT: Agent,
    ResourceKind.WORKFLOW: Workflow,
    ResourceKind.SKILL: Skill,
    ResourceKind.CAPABILITY: Capability,
    ResourceKind.KNOWLEDGE: Knowledge,
    ResourceKind.MODEL_PROFILE: ModelProfile,
    ResourceKind.PROMPT: Prompt,
    ResourceKind.POLICY: Policy,
    ResourceKind.OUTPUT_SCHEMA: OutputSchema,
    ResourceKind.CAPABILITY_BINDING: CapabilityBinding,
}


def _issues_from_validation_error(exc: ValidationError) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for err in exc.errors():
        location = ".".join(str(p) for p in err["loc"])
        issues.append(
            ValidationIssue(
                code=ErrorCode.SCHEMA_INVALID,
                message=err["msg"],
                location=location,
            )
        )
    return issues


def parse_resource(data: dict[str, Any]) -> EapResource:
    """Parse a single resource dict into its typed model."""
    if not isinstance(data, dict):
        raise SpecValidationError(
            [ValidationIssue(ErrorCode.SCHEMA_INVALID, "document must be a mapping")]
        )
    kind_raw = data.get("kind")
    if not kind_raw:
        raise SpecValidationError(
            [ValidationIssue(ErrorCode.SCHEMA_INVALID, "missing 'kind'", "kind")]
        )
    try:
        kind = ResourceKind(kind_raw)
    except ValueError as exc:
        valid = ", ".join(k.value for k in KIND_MODELS)
        raise SpecValidationError(
            [ValidationIssue(ErrorCode.SCHEMA_INVALID, f"unknown kind {kind_raw!r}; valid: {valid}", "kind")]
        ) from exc

    model_cls = KIND_MODELS[kind]
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise SpecValidationError(_issues_from_validation_error(exc)) from exc


def load_yaml(text: str) -> EapResource:
    """Parse a single-document YAML string into a typed resource."""
    data = yaml.safe_load(text)
    return parse_resource(data)


def load_yaml_documents(text: str) -> list[EapResource]:
    """Parse a multi-document YAML string (``---`` separated) into resources."""
    resources: list[EapResource] = []
    for doc in yaml.safe_load_all(text):
        if doc is None:
            continue
        resources.append(parse_resource(doc))
    return resources


def load_file(path: str | Path) -> list[EapResource]:
    """Load one or more resources from a YAML file."""
    text = Path(path).read_text(encoding="utf-8")
    return load_yaml_documents(text)


def to_model(data: dict[str, Any] | BaseModel) -> EapResource:
    """Coerce a dict or already-parsed model into a typed resource."""
    if isinstance(data, EapResource):
        return data
    if isinstance(data, dict):
        return parse_resource(data)
    raise SpecValidationError(
        [ValidationIssue(ErrorCode.SCHEMA_INVALID, f"cannot parse {type(data).__name__}")]
    )
