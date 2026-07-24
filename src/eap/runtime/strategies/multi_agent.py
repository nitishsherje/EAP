"""MultiAgentStrategy - coordinates multiple collaborating agents.

Stub behind the ExecutionStrategy interface. Multi-agent orchestration mechanics
(hand-off, group chat, planner/worker) are provided by Microsoft Agent Framework;
this strategy will map a resolved multi-agent definition onto those primitives.
"""

from __future__ import annotations

from eap.common.errors import ErrorCode, ExecutionError
from eap.runtime.context import ExecutionContext
from eap.runtime.deps import RuntimeServices
from eap.runtime.models import ExecutionResult
from eap.runtime.strategies.base import ExecutionStrategy


class MultiAgentStrategy(ExecutionStrategy):
    name = "multi_agent"

    def execute(self, ctx: ExecutionContext, services: RuntimeServices) -> ExecutionResult:
        raise ExecutionError(
            "MultiAgentStrategy is not implemented in MVP1; delegate to MAF multi-agent primitives.",
            code=ErrorCode.STRATEGY_UNKNOWN,
        )
