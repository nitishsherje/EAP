"""Security & governance primitives (Layer 1, cross-cutting).

Provides authentication, secret resolution, guardrails, data classification and
audit logging as injectable interfaces. Defaults are dev-friendly; production
wires enterprise IAM/SSO and the enterprise secrets manager. RBAC/ABAC policy
*evaluation* lives in the control-plane governance module, which consumes the
``Principal`` produced here.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from eap.common.errors import AuthenticationError


@dataclass(frozen=True)
class Principal:
    """An authenticated caller."""

    subject: str
    roles: frozenset[str] = frozenset()
    tenant: str = "default"
    attributes: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def system() -> Principal:
        return Principal(subject="system", roles=frozenset({"platform-admin"}))

    @staticmethod
    def anonymous() -> Principal:
        return Principal(subject="anonymous", roles=frozenset())


class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


# --------------------------------------------------------------------------- #
# Secrets                                                                      #
# --------------------------------------------------------------------------- #
class SecretsProvider(ABC):
    """Resolves a logical secret name to its value at runtime.

    Specs and bindings only ever carry secret *names*; the value is fetched here.
    """

    @abstractmethod
    def get_secret(self, name: str) -> str | None: ...


class EnvSecretsProvider(SecretsProvider):
    """Reads secrets from environment variables.

    Lookup order for a logical ``secret_ref`` name:
      1. ``EAP_SECRET_<UPPER_NAME>`` (dashes → underscores)
      2. Well-known aliases (e.g. ``LLM_GATEWAY_API_KEY``, ``DOCLING_API_KEY``)

    Suitable for local/dev and for K8s env-injected secrets. Replace with the
    enterprise secrets manager in production.
    """

    _ALIASES: dict[str, tuple[str, ...]] = {
        "llm-gateway-oauth": ("LLM_GATEWAY_API_KEY", "EAP_LLM_GATEWAY_API_KEY"),
        "llm_gateway_oauth": ("LLM_GATEWAY_API_KEY", "EAP_LLM_GATEWAY_API_KEY"),
        "docling-oauth": ("DOCLING_API_KEY", "EAP_DOCLING_API_KEY"),
        "docling_oauth": ("DOCLING_API_KEY", "EAP_DOCLING_API_KEY"),
        "milvus-api-key": ("MILVUS_API_KEY", "EAP_MILVUS_API_KEY"),
    }

    def __init__(self, prefix: str = "EAP_SECRET_") -> None:
        self._prefix = prefix

    def get_secret(self, name: str) -> str | None:
        env_key = self._prefix + name.upper().replace("-", "_")
        value = os.environ.get(env_key)
        if value:
            return value
        for alias in self._ALIASES.get(name, ()) + self._ALIASES.get(name.replace("_", "-"), ()):
            alias_val = os.environ.get(alias)
            if alias_val:
                return alias_val
        return None


# --------------------------------------------------------------------------- #
# Authentication                                                               #
# --------------------------------------------------------------------------- #
class Authenticator(ABC):
    @abstractmethod
    def authenticate(self, token: str | None) -> Principal: ...


class AllowAllAuthenticator(Authenticator):
    """Dev authenticator: maps any token to a system principal, none to anonymous."""

    def authenticate(self, token: str | None) -> Principal:
        return Principal.system() if token else Principal.anonymous()


class BearerTokenAuthenticator(Authenticator):
    """Placeholder for enterprise SSO/OIDC token validation."""

    def authenticate(self, token: str | None) -> Principal:  # pragma: no cover - stub
        if not token:
            raise AuthenticationError("missing bearer token")
        raise NotImplementedError("Wire enterprise OIDC/SSO validation here.")


# --------------------------------------------------------------------------- #
# Guardrails                                                                   #
# --------------------------------------------------------------------------- #
@dataclass
class GuardrailResult:
    allowed: bool = True
    content: str = ""
    violations: list[str] = field(default_factory=list)


class Guardrail(ABC):
    @abstractmethod
    def check(self, content: str, rules: list[dict]) -> GuardrailResult: ...


class NoopGuardrail(Guardrail):
    """Default guardrail: passes content through unchanged.

    Real content-safety/PII enforcement plugs in here without changing callers.
    """

    def check(self, content: str, rules: list[dict]) -> GuardrailResult:
        return GuardrailResult(allowed=True, content=content)


# --------------------------------------------------------------------------- #
# Audit                                                                        #
# --------------------------------------------------------------------------- #
class AuditLogger(ABC):
    @abstractmethod
    def record(self, action: str, principal: Principal, resource: str, **details) -> None: ...


class LoggingAuditLogger(AuditLogger):
    def __init__(self) -> None:
        import logging

        self._log = logging.getLogger("eap.audit")

    def record(self, action: str, principal: Principal, resource: str, **details) -> None:
        self._log.info(
            "audit action=%s subject=%s tenant=%s resource=%s details=%s",
            action,
            principal.subject,
            principal.tenant,
            resource,
            details,
        )


__all__ = [
    "AllowAllAuthenticator",
    "AuditLogger",
    "Authenticator",
    "BearerTokenAuthenticator",
    "DataClassification",
    "EnvSecretsProvider",
    "Guardrail",
    "GuardrailResult",
    "LoggingAuditLogger",
    "NoopGuardrail",
    "Principal",
    "SecretsProvider",
]
