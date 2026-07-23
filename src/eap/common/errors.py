"""Structured error model shared across all EAP layers.

Every failure surfaces as an :class:`EapError` carrying a stable ``code`` so the
API layer and observability can translate it consistently. Validation issues are
collected (not raised one-at-a-time) so a spec author sees every problem at once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ErrorCode(str, Enum):
    """Stable machine-readable error codes."""

    # Specification / validation
    SCHEMA_INVALID = "spec.schema_invalid"
    SEMANTIC_INVALID = "spec.semantic_invalid"
    REFERENCE_INVALID = "spec.reference_invalid"
    REFERENCE_UNRESOLVED = "spec.reference_unresolved"
    VERSION_INVALID = "spec.version_invalid"
    COMPATIBILITY_BROKEN = "spec.compatibility_broken"

    # Registry / lifecycle
    NOT_FOUND = "registry.not_found"
    ALREADY_EXISTS = "registry.already_exists"
    LIFECYCLE_INVALID = "lifecycle.invalid_transition"

    # Governance / security
    POLICY_DENIED = "governance.policy_denied"
    UNAUTHENTICATED = "security.unauthenticated"
    UNAUTHORIZED = "security.unauthorized"
    GUARDRAIL_BLOCKED = "security.guardrail_blocked"

    # Resolution
    RESOLUTION_FAILED = "resolver.failed"
    BINDING_MISSING = "resolver.binding_missing"

    # Runtime / execution
    EXECUTION_FAILED = "runtime.execution_failed"
    STRATEGY_UNKNOWN = "runtime.strategy_unknown"
    HITL_REQUIRED = "runtime.hitl_required"

    # Capabilities / providers / adapters
    CAPABILITY_UNKNOWN = "capability.unknown"
    OPERATION_UNKNOWN = "capability.operation_unknown"
    ADAPTER_ERROR = "adapter.error"
    PROVIDER_ERROR = "provider.error"

    # Generic
    INTERNAL = "internal.error"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    """A single, addressable problem found while validating a spec."""

    code: ErrorCode
    message: str
    location: str = ""  # dotted path into the document, e.g. "spec.skills[0].ref"
    severity: Severity = Severity.ERROR

    def __str__(self) -> str:
        loc = f" at '{self.location}'" if self.location else ""
        return f"[{self.code.value}]{loc}: {self.message}"


class EapError(Exception):
    """Base class for all EAP errors."""

    default_code: ErrorCode = ErrorCode.INTERNAL

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.details = details or {}

    def to_dict(self) -> dict:
        return {"code": self.code.value, "message": self.message, "details": self.details}


class SpecValidationError(EapError):
    """Raised when a spec fails validation. Carries every issue found."""

    default_code = ErrorCode.SCHEMA_INVALID

    def __init__(self, issues: list[ValidationIssue], message: str = "Specification validation failed"):
        super().__init__(message, code=ErrorCode.SCHEMA_INVALID)
        self.issues = issues

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["issues"] = [
            {
                "code": i.code.value,
                "message": i.message,
                "location": i.location,
                "severity": i.severity.value,
            }
            for i in self.issues
        ]
        return data


class NotFoundError(EapError):
    default_code = ErrorCode.NOT_FOUND


class AlreadyExistsError(EapError):
    default_code = ErrorCode.ALREADY_EXISTS


class ResolutionError(EapError):
    default_code = ErrorCode.RESOLUTION_FAILED


class PolicyDeniedError(EapError):
    default_code = ErrorCode.POLICY_DENIED


class AuthenticationError(EapError):
    default_code = ErrorCode.UNAUTHENTICATED


class AuthorizationError(EapError):
    default_code = ErrorCode.UNAUTHORIZED


class GuardrailError(EapError):
    default_code = ErrorCode.GUARDRAIL_BLOCKED


class ExecutionError(EapError):
    default_code = ErrorCode.EXECUTION_FAILED


class AdapterError(EapError):
    default_code = ErrorCode.ADAPTER_ERROR


class ProviderError(EapError):
    default_code = ErrorCode.PROVIDER_ERROR


class CapabilityError(EapError):
    default_code = ErrorCode.CAPABILITY_UNKNOWN


@dataclass
class ValidationResult:
    """Aggregate result of a validation pass."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity is Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)

    def error(self, code: ErrorCode, message: str, location: str = "") -> None:
        self.add(ValidationIssue(code, message, location, Severity.ERROR))

    def warn(self, code: ErrorCode, message: str, location: str = "") -> None:
        self.add(ValidationIssue(code, message, location, Severity.WARNING))

    def merge(self, other: ValidationResult) -> None:
        self.issues.extend(other.issues)

    def raise_if_failed(self) -> None:
        if not self.ok:
            raise SpecValidationError(self.errors)
