"""ExecutionStrategy - pluggable execution shapes.

The coordinator selects a strategy from the ResolvedDefinition. Strategies build
the framework invocation and delegate agent mechanics to the AgentFrameworkAdapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from eap.runtime.context import ExecutionContext
from eap.runtime.deps import RuntimeServices
from eap.runtime.models import ExecutionResult


class ExecutionStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def execute(self, ctx: ExecutionContext, services: RuntimeServices) -> ExecutionResult: ...
