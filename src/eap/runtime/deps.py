"""RuntimeServices - the dependency bundle passed to strategies.

Keeps the ExecutionCoordinator and strategies decoupled from how services are
constructed (that is the composition root's job in api_gateway).
"""

from __future__ import annotations

from dataclasses import dataclass

from eap.capabilities import CapabilityManager
from eap.common.config import Settings
from eap.common.events import EventPublisher
from eap.knowledge import KnowledgeService
from eap.observability import Telemetry
from eap.persistence.base import MetadataRepository
from eap.providers.llm import ModelProvider
from eap.runtime.context import ContextService
from eap.runtime.framework import AgentFrameworkAdapter
from eap.runtime.hitl import HITLService
from eap.runtime.memory import MemoryService
from eap.runtime.response import ResponseService
from eap.runtime.state import StateCheckpointService
from eap.security import SecretsProvider


@dataclass
class RuntimeServices:
    settings: Settings
    secrets: SecretsProvider
    model_provider: ModelProvider
    capability_manager: CapabilityManager
    knowledge_service: KnowledgeService
    context_service: ContextService
    memory_service: MemoryService
    state_service: StateCheckpointService
    hitl_service: HITLService
    response_service: ResponseService
    framework: AgentFrameworkAdapter
    events: EventPublisher
    telemetry: Telemetry
    metadata_repo: MetadataRepository
