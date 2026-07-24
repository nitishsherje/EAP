"""Semantic versioning rules for EAP resources.

Every registered resource has an immutable ``major.minor.patch`` version.
References may request an exact version, a partial constraint (``1`` or ``1.2``),
or an alias (``latest`` / ``stable``) which the resolver maps to a concrete
version. Nothing executes against a non-pinned version.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering

_SEMVER_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
_PARTIAL_RE = re.compile(r"^(?P<major>\d+)(?:\.(?P<minor>\d+))?$")

ALIASES = frozenset({"latest", "stable"})


@total_ordering
@dataclass(frozen=True, order=False)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> SemVer:
        m = _SEMVER_RE.match(value.strip())
        if not m:
            raise ValueError(f"Invalid semantic version: {value!r} (expected MAJOR.MINOR.PATCH)")
        return cls(int(m["major"]), int(m["minor"]), int(m["patch"]))

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return bool(_SEMVER_RE.match(value.strip()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def bump_major(self) -> SemVer:
        return SemVer(self.major + 1, 0, 0)

    def bump_minor(self) -> SemVer:
        return SemVer(self.major, self.minor + 1, 0)

    def bump_patch(self) -> SemVer:
        return SemVer(self.major, self.minor, self.patch + 1)


class Compatibility:
    """SemVer compatibility rules used by the compatibility validator."""

    @staticmethod
    def is_breaking(old: SemVer, new: SemVer) -> bool:
        """A major bump signals a breaking change."""
        return new.major != old.major

    @staticmethod
    def is_backward_compatible(old: SemVer, new: SemVer) -> bool:
        return new.major == old.major and new >= old


def matches_constraint(candidate: SemVer, constraint: str) -> bool:
    """Return True if ``candidate`` satisfies a partial/exact constraint string."""
    constraint = constraint.strip()
    if SemVer.is_valid(constraint):
        return candidate == SemVer.parse(constraint)
    m = _PARTIAL_RE.match(constraint)
    if not m:
        return False
    if candidate.major != int(m["major"]):
        return False
    return not (m["minor"] is not None and candidate.minor != int(m["minor"]))


def select_version(available: list[SemVer], requested: str | None) -> SemVer | None:
    """Resolve a requested version/alias/constraint to a concrete pinned version.

    - ``None`` / ``latest`` / ``stable`` -> highest available version
    - exact semver -> that version if present
    - partial constraint (``1`` / ``1.2``) -> highest matching version
    """
    if not available:
        return None
    ordered = sorted(available, reverse=True)
    if requested is None or requested in ALIASES:
        return ordered[0]
    if SemVer.is_valid(requested):
        target = SemVer.parse(requested)
        return target if target in available else None
    matching = [v for v in ordered if matches_constraint(v, requested)]
    return matching[0] if matching else None
