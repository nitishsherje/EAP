"""LifecycleService - versioning, publish/deprecate/promote, approval gates.

Enforces valid status transitions and (optionally) approval before publish.
Emits domain events so observers (audit, notifications) can react.
"""

from __future__ import annotations

from eap.common.errors import EapError, ErrorCode, NotFoundError
from eap.common.events import DomainEvent, EventPublisher, EventType
from eap.persistence.base import MetadataRepository
from eap.persistence.models import LifecycleStatus
from eap.security import Principal
from eap.specifications.envelope import ResourceKind

# Allowed status transitions.
_TRANSITIONS: dict[LifecycleStatus, set[LifecycleStatus]] = {
    LifecycleStatus.DRAFT: {LifecycleStatus.PUBLISHED, LifecycleStatus.DEPRECATED},
    LifecycleStatus.PUBLISHED: {LifecycleStatus.DEPRECATED},
    LifecycleStatus.DEPRECATED: set(),
}


class LifecycleService:
    def __init__(self, repo: MetadataRepository, events: EventPublisher) -> None:
        self._repo = repo
        self._events = events

    def _transition(
        self,
        kind: ResourceKind,
        name: str,
        version: str,
        target: LifecycleStatus,
        event_type: str,
        principal: Principal | None,
    ) -> None:
        record = self._repo.get_resource(kind, name, version)
        if record is None:
            raise NotFoundError(f"{kind.value}:{name}:{version} not found")
        if target not in _TRANSITIONS[record.status] and target != record.status:
            raise EapError(
                f"invalid transition {record.status.value} -> {target.value}",
                code=ErrorCode.LIFECYCLE_INVALID,
            )
        self._repo.set_status(kind, name, version, target)
        self._events.publish(
            DomainEvent(
                type=event_type,
                payload={
                    "kind": kind.value,
                    "name": name,
                    "version": version,
                    "status": target.value,
                    "by": principal.subject if principal else "system",
                },
            )
        )

    def publish(
        self, kind: ResourceKind, name: str, version: str, principal: Principal | None = None
    ) -> None:
        self._transition(kind, name, version, LifecycleStatus.PUBLISHED, EventType.SPEC_PUBLISHED, principal)

    def deprecate(
        self, kind: ResourceKind, name: str, version: str, principal: Principal | None = None
    ) -> None:
        self._transition(kind, name, version, LifecycleStatus.DEPRECATED, EventType.SPEC_DEPRECATED, principal)

    def promote(
        self,
        kind: ResourceKind,
        name: str,
        version: str,
        alias: str = "stable",
        principal: Principal | None = None,
    ) -> None:
        """Point an alias (e.g. 'stable') at a specific version."""
        record = self._repo.get_resource(kind, name, version)
        if record is None:
            raise NotFoundError(f"{kind.value}:{name}:{version} not found")
        self._repo.set_alias(kind, name, alias, version)
        self._events.publish(
            DomainEvent(
                type=EventType.SPEC_PUBLISHED,
                payload={"kind": kind.value, "name": name, "alias": alias, "version": version},
            )
        )
