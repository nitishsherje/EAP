"""Composition root - wires all layers into a runnable application.

This is the only place allowed to depend on every layer. It constructs the
control plane, runtime and cross-cutting services, selecting real vs. fake
backends from Settings.
"""

from __future__ import annotations

import json
from pathlib import Path

from eap.capabilities import CapabilityManager
from eap.common.config import Settings
from eap.common.events import InProcessEventBus
from eap.control_plane import ControlPlane
from eap.evaluation import Feedback, FeedbackService
from eap.knowledge import KnowledgeService
from eap.observability import Telemetry, TokenTracker, configure_logging
from eap.persistence import (
    build_artifact_store,
    build_metadata_repository,
    build_state_store,
)
from eap.persistence.models import LifecycleStatus
from eap.providers.llm import ModelProvider
from eap.runtime import (
    ContextService,
    ExecutionCoordinator,
    ExecutionRequest,
    ExecutionResult,
    HITLService,
    InProcessAgentFramework,
    MemoryService,
    ResponseService,
    RuntimeServices,
    StateCheckpointService,
)
from eap.security import (
    AllowAllAuthenticator,
    EnvSecretsProvider,
    LoggingAuditLogger,
    NoopGuardrail,
    Principal,
)
from eap.specifications.envelope import EapResource, ResourceKind
from eap.specifications.loader import load_file
from eap.specifications.resolved_definition import ResolvedDefinition


class EapApplication:
    """The assembled EAP platform (single-process modular monolith)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.load()
        configure_logging()

        # Cross-cutting.
        self.events = InProcessEventBus()
        self.audit = LoggingAuditLogger()
        self.secrets = EnvSecretsProvider()
        self.telemetry = Telemetry(self.settings.otel_enabled)
        self.token_tracker = TokenTracker()
        self.authenticator = AllowAllAuthenticator()
        self.feedback = FeedbackService(self.events)
        guardrail = NoopGuardrail()

        # Persistence.
        self.metadata_repo = build_metadata_repository(self.settings)
        self.artifacts = build_artifact_store(self.settings)
        self.state_store = build_state_store(self.settings)

        # Control plane.
        self.control_plane = ControlPlane(
            self.metadata_repo,
            self.events,
            self.audit,
            enforce_policies=self.settings.auth_enabled,
        )

        # Layer 4 services.
        self.model_provider = ModelProvider(
            self.settings, self.secrets, self.token_tracker, self.telemetry
        )
        self.capability_manager = CapabilityManager(
            self.settings, self.secrets, guardrail, self.telemetry
        )
        self.knowledge_service = KnowledgeService(
            self.settings, self.secrets, telemetry=self.telemetry
        )

        # Runtime.
        self.services = RuntimeServices(
            settings=self.settings,
            secrets=self.secrets,
            model_provider=self.model_provider,
            capability_manager=self.capability_manager,
            knowledge_service=self.knowledge_service,
            context_service=ContextService(),
            memory_service=MemoryService(),
            state_service=StateCheckpointService(self.state_store),
            hitl_service=HITLService(self.events, auto_approve=True),
            response_service=ResponseService(guardrail),
            framework=InProcessAgentFramework(),
            events=self.events,
            telemetry=self.telemetry,
            metadata_repo=self.metadata_repo,
        )
        self.coordinator = ExecutionCoordinator(self.services)

    # --- authentication ---
    def authenticate(self, token: str | None) -> Principal:
        return self.authenticator.authenticate(token)

    # --- feedback capture ---
    def record_feedback(self, run_id: str, rating: int, comment: str = "", subject: str = "anonymous") -> Feedback:
        return self.feedback.record(run_id, rating, comment, subject)

    # --- control plane operations ---
    def register(
        self, resource: EapResource, principal: Principal | None = None, publish: bool = False
    ) -> None:
        self.control_plane.register(resource, principal or Principal.system())
        if publish and resource.kind != ResourceKind.CAPABILITY_BINDING:
            self.control_plane.publish(resource, principal or Principal.system())

    def load_directory(self, path: str | Path, publish: bool = True) -> int:
        count = 0
        for file in sorted(Path(path).rglob("*.yaml")):
            for resource in load_file(file):
                self.register(resource, publish=publish)
                count += 1
        return count

    def resolve(
        self, ref: str, environment: str | None = None, principal: Principal | None = None
    ) -> ResolvedDefinition:
        env = environment or self.settings.environment
        rd = self.control_plane.resolve(ref, env, principal or Principal.system())
        # Persist the immutable artifact.
        self.artifacts.put(
            f"resolved/{rd.content_hash}.json",
            json.dumps(rd.model_dump(mode="json")).encode("utf-8"),
        )
        return rd

    # --- runtime operations ---
    def run_resolved(self, rd: ResolvedDefinition, request: ExecutionRequest) -> ExecutionResult:
        return self.coordinator.run(rd, request)

    def run_agent(
        self,
        ref: str,
        query: str = "",
        inputs: dict | None = None,
        principal: Principal | None = None,
        environment: str | None = None,
    ) -> ExecutionResult:
        return self._run_target(ref, query, inputs, principal, environment)

    def run_workflow(
        self,
        ref: str,
        query: str = "",
        inputs: dict | None = None,
        principal: Principal | None = None,
        environment: str | None = None,
    ) -> ExecutionResult:
        return self._run_target(ref, query, inputs, principal, environment)

    def _run_target(
        self,
        ref: str,
        query: str,
        inputs: dict | None,
        principal: Principal | None,
        environment: str | None,
    ) -> ExecutionResult:
        principal = principal or Principal.system()
        rd = self.resolve(ref, environment, principal)
        request = ExecutionRequest(
            inputs=inputs or {},
            query=query,
            principal=principal,
            environment=rd.environment,
        )
        return self.coordinator.run(rd, request)


def build_app(settings: Settings | None = None) -> EapApplication:
    return EapApplication(settings)


def build_app_with_examples(settings: Settings | None = None) -> EapApplication:
    """Build an app and register the bundled example contracts."""
    app = build_app(settings)
    contracts_dir = Path(__file__).resolve().parents[3] / "contracts"
    app.load_directory(contracts_dir, publish=True)
    return app


# Re-export so callers can reference statuses without importing persistence.
__all__ = ["EapApplication", "LifecycleStatus", "build_app", "build_app_with_examples"]
