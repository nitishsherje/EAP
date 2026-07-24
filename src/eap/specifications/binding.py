"""CapabilityBinding - environment-specific wiring for a logical resource.

Bindings are where physical concerns live: which adapter, which endpoint, which
secret (by *reference*, never the secret itself), timeouts and limits. Bindings
are environment-scoped (dev/qa/prod) and injected during resolution so the same
spec runs unchanged across environments.

    target: capability://document-intelligence/1.0.0
    environment: prod
    adapter: docling
    auth: { type: oauth, secret_ref: docling-oauth }
"""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from eap.specifications.envelope import EapResource, ResourceKind
from eap.specifications.references import Reference, ReferenceError, Scheme

# Bindings may target capabilities, knowledge sources, or model profiles.
_BINDABLE_SCHEMES = {Scheme.CAPABILITY, Scheme.KNOWLEDGE, Scheme.MODEL}


class AuthType(str, Enum):
    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    IAM = "iam"  # enterprise IAM / instance role


class AuthBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: AuthType = AuthType.NONE
    # Logical name resolved by the SecretsProvider at runtime. NEVER a literal secret.
    secret_ref: str | None = None
    scopes: list[str] = Field(default_factory=list)

    @field_validator("secret_ref")
    @classmethod
    def _no_inline_secret(cls, v: str | None) -> str | None:
        if v and any(token in v for token in ("://", " ", "=")):
            raise ValueError(
                "auth.secret_ref must be a logical secret name, not an inline secret/URL"
            )
        return v


class BindingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str  # capability:// | knowledge:// | model:// (may be partial version)
    environment: str
    adapter: str  # adapter id, e.g. "docling", "milvus", "enterprise_api", "llm_gateway"
    endpoint: str | None = None  # non-secret logical endpoint/host
    auth: AuthBinding = Field(default_factory=AuthBinding)
    config: dict[str, Any] = Field(default_factory=dict)  # non-secret config
    timeout_seconds: float = 30.0
    max_retries: int = 2
    rate_limit_per_min: int | None = None

    @field_validator("target")
    @classmethod
    def _v_target(cls, v: str) -> str:
        try:
            ref = Reference.parse(v)
        except ReferenceError as exc:
            raise ValueError(str(exc)) from exc
        if ref.scheme not in _BINDABLE_SCHEMES:
            allowed = ", ".join(s.value for s in _BINDABLE_SCHEMES)
            raise ValueError(f"binding target must be one of: {allowed}")
        return v


class CapabilityBinding(EapResource):
    expected_kind: ClassVar[ResourceKind] = ResourceKind.CAPABILITY_BINDING

    kind: ResourceKind = ResourceKind.CAPABILITY_BINDING
    spec: BindingSpec

    @property
    def target_ref(self) -> Reference:
        return Reference.parse(self.spec.target)
