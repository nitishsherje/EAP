"""Reference grammar and parser.

Specifications use *logical* references, never physical endpoints. Grammar:

    <scheme>://<name>[/<version-or-alias>]

Examples:
    agent://auditor-report-agent/1.0.0
    skill://auditor-extraction/2.1.0
    capability://document-intelligence/1.0.0
    knowledge://ratings-knowledge/2.0.0
    model://reasoning-standard/1.0.0
    prompt://auditor-analysis            (version omitted -> resolves to latest)

The version part may be an exact semver, a partial constraint (``1`` / ``1.2``),
or an alias (``latest`` / ``stable``). It is resolved to an immutable pinned
version by the Control Plane resolver before execution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_REF_RE = re.compile(r"^(?P<scheme>[a-z]+)://(?P<name>[^/]+)(?:/(?P<version>[^/]+))?$")


class Scheme(str, Enum):
    AGENT = "agent"
    WORKFLOW = "workflow"
    SKILL = "skill"
    CAPABILITY = "capability"
    KNOWLEDGE = "knowledge"
    MODEL = "model"
    PROMPT = "prompt"
    POLICY = "policy"
    SCHEMA = "schema"


# Which resource kind each scheme resolves to (used by validators/resolver).
SCHEME_KINDS: dict[Scheme, str] = {
    Scheme.AGENT: "Agent",
    Scheme.WORKFLOW: "Workflow",
    Scheme.SKILL: "Skill",
    Scheme.CAPABILITY: "Capability",
    Scheme.KNOWLEDGE: "Knowledge",
    Scheme.MODEL: "ModelProfile",
    Scheme.PROMPT: "Prompt",
    Scheme.POLICY: "Policy",
    Scheme.SCHEMA: "OutputSchema",
}


class ReferenceError(ValueError):
    """Raised when a reference string is malformed."""


@dataclass(frozen=True)
class Reference:
    """A parsed logical reference. Immutable value object."""

    scheme: Scheme
    name: str
    version: str | None = None  # exact | partial | alias | None

    @classmethod
    def parse(cls, value: str) -> Reference:
        if not isinstance(value, str):
            raise ReferenceError(f"Reference must be a string, got {type(value).__name__}")
        m = _REF_RE.match(value.strip())
        if not m:
            raise ReferenceError(
                f"Malformed reference {value!r}. Expected '<scheme>://<name>[/<version>]'."
            )
        scheme_raw = m["scheme"]
        try:
            scheme = Scheme(scheme_raw)
        except ValueError as exc:
            valid = ", ".join(s.value for s in Scheme)
            raise ReferenceError(
                f"Unknown reference scheme {scheme_raw!r}. Valid schemes: {valid}."
            ) from exc
        name = m["name"]
        if not _NAME_RE.match(name):
            raise ReferenceError(
                f"Invalid reference name {name!r}. Use lowercase alphanumerics, '.', '-', '_'."
            )
        return cls(scheme=scheme, name=name, version=m["version"])

    @classmethod
    def is_valid(cls, value: str) -> bool:
        try:
            cls.parse(value)
            return True
        except ReferenceError:
            return False

    @property
    def kind(self) -> str:
        return SCHEME_KINDS[self.scheme]

    @property
    def is_pinned(self) -> bool:
        from eap.specifications.versioning import SemVer

        return self.version is not None and SemVer.is_valid(self.version)

    def with_version(self, version: str) -> Reference:
        return Reference(self.scheme, self.name, version)

    def __str__(self) -> str:
        base = f"{self.scheme.value}://{self.name}"
        return f"{base}/{self.version}" if self.version else base
