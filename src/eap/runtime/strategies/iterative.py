"""IterativeStrategy - repeats reasoning until a stop condition is met.

Stub behind the ExecutionStrategy interface. The iterate/refine loop mechanics are
provided by Microsoft Agent Framework; this strategy will govern the iteration
budget and stop conditions from the resolved definition.
"""

from __future__ import annotations

from eap.common.errors import ErrorCode, ExecutionError
from eap.runtime.context import ExecutionContext
from eap.runtime.deps import RuntimeServices
from eap.runtime.models import ExecutionResult
from eap.runtime.strategies.base import ExecutionStrategy


class IterativeStrategy(ExecutionStrategy):
    name = "iterative"

    def execute(self, ctx: ExecutionContext, services: RuntimeServices) -> ExecutionResult:
        raise ExecutionError(
            "IterativeStrategy is not implemented in MVP1; delegate to MAF iterate primitives.",
            code=ErrorCode.STRATEGY_UNKNOWN,
        )
