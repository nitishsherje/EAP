"""Control Plane (Layer 2) - validate, register, resolve, govern.

Facade that composes the logical control-plane modules. These are modules, not
microservices; they are deployed inside the EAP service in MVP1.
"""

from __future__ import annotations

from eap.common.events import DomainEvent, EventPublisher, EventType
from eap.control_plane.catalog import Catalog
from eap.control_plane.governance import GovernanceService
from eap.control_plane.lifecycle import LifecycleService
from eap.control_plane.registry import Registry
from eap.control_plane.resolver import Resolver
from eap.control_plane.spec_service import SpecificationService
from eap.persistence.base import MetadataRepository
from eap.persistence.models import LifecycleStatus, ResourceRecord
from eap.security import AuditLogger, Principal
from eap.specifications.envelope import EapResource
from eap.specifications.resolved_definition import ResolvedDefinition


class ControlPlane:
    def __init__(
        self,
        repo: MetadataRepository,
        events: EventPublisher,
        audit: AuditLogger,
        enforce_policies: bool = False,
    ) -> None:
        self._repo = repo
        self._events = events
        self.registry = Registry(repo)
        self.catalog = Catalog(self.registry)
        self.spec_service = SpecificationService(self.registry)
        self.governance = GovernanceService(audit, enforce=enforce_policies)
        self.resolver = Resolver(self.registry, self.governance)
        self.lifecycle = LifecycleService(repo, events)

    def register(
        self,
        resource: EapResource,
        principal: Principal | None = None,
        status: LifecycleStatus = LifecycleStatus.DRAFT,
    ) -> ResourceRecord:
        record = self.spec_service.ingest(resource, principal=principal, status=status)
        self._events.publish(
            DomainEvent(
                type=EventType.SPEC_REGISTERED,
                payload={"key": record.key, "by": (principal or Principal.system()).subject},
            )
        )
        return record

    def publish(
        self, resource: EapResource, principal: Principal | None = None
    ) -> None:
        self.lifecycle.publish(
            resource.kind, resource.metadata.name, resource.metadata.version, principal
        )

    def resolve(
        self,
        ref: str,
        environment: str = "dev",
        principal: Principal | None = None,
        *,
        published_only: bool = True,
    ) -> ResolvedDefinition:
        definition = self.resolver.resolve(
            ref, environment=environment, principal=principal, published_only=published_only
        )
        self._events.publish(
            DomainEvent(
                type=EventType.AGENT_RESOLVED,
                payload={"target": definition.target, "hash": definition.content_hash},
            )
        )
        return definition


__all__ = [
    "Catalog",
    "ControlPlane",
    "GovernanceService",
    "LifecycleService",
    "Registry",
    "Resolver",
    "SpecificationService",
]
