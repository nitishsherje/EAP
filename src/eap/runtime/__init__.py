"""EAP Runtime (Layer 5) - execution of ResolvedDefinitions.

Delegates agent mechanics to Microsoft Agent Framework via the
AgentFrameworkAdapter; never imports the control plane.
"""

from eap.runtime.context import ContextService, ExecutionContext
from eap.runtime.deps import RuntimeServices
from eap.runtime.execution import ExecutionCoordinator
from eap.runtime.framework import (
    AgentFrameworkAdapter,
    InProcessAgentFramework,
)
from eap.runtime.hitl import HITLService
from eap.runtime.memory import MemoryService
from eap.runtime.models import ExecutionRequest, ExecutionResult
from eap.runtime.response import ResponseService
from eap.runtime.state import StateCheckpointService

__all__ = [
    "AgentFrameworkAdapter",
    "ContextService",
    "ExecutionContext",
    "ExecutionCoordinator",
    "ExecutionRequest",
    "ExecutionResult",
    "HITLService",
    "InProcessAgentFramework",
    "MemoryService",
    "ResponseService",
    "RuntimeServices",
    "StateCheckpointService",
]
