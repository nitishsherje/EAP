"""ModelProfile - a governed, logical model configuration.

Agents/skills reference ``model://<name>/<version>`` instead of a vendor/model
id. The profile captures model-invocation concerns (routing, params, fallback,
structured output) that are distinct from tool invocation. The physical model
endpoint/credentials are supplied at bind time, not here.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from eap.specifications.envelope import EapResource, ResourceKind, reference_field_validator
from eap.specifications.references import Scheme


class ModelParameters(BaseModel):
    model_config = ConfigDict(extra="allow")  # vendor-neutral, extensible params

    temperature: float = 0.2
    max_tokens: int | None = None
    top_p: float | None = None


class ModelProfileSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Logical model id served by the LLM gateway (e.g. "reasoning-standard").
    model: str
    provider: str = "crisil-llm-gateway"
    parameters: ModelParameters = Field(default_factory=ModelParameters)
    # Ordered fallback model profiles (model:// refs) if the primary is unavailable.
    fallback: list[str] = Field(default_factory=list)
    structured_output: bool = False

    @field_validator("fallback")
    @classmethod
    def _validate_fallback(cls, v: list[str]) -> list[str]:
        validate = reference_field_validator(Scheme.MODEL)
        return [validate(item) for item in v]


class ModelProfile(EapResource):
    expected_kind: ClassVar[ResourceKind] = ResourceKind.MODEL_PROFILE

    kind: ResourceKind = ResourceKind.MODEL_PROFILE
    spec: ModelProfileSpec
