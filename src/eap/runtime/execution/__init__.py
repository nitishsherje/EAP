"""ExecutionCoordinator - the runtime entry point.

Load ResolvedDefinition -> verify integrity -> create context -> select strategy
-> delegate mechanics to Microsoft Agent Framework -> coordinate state/HITL ->
produce governed result. Enforces the invariant that ONLY an integrity-verified
ResolvedDefinition may execute.
"""

from __future__ import annotations

from eap.common.errors import EapError, ErrorCode, ExecutionError
from eap.common.events import DomainEvent, EventType
from eap.persistence.models import RunRecord, RunStatus
from eap.runtime.deps import RuntimeServices
from eap.runtime.models import ExecutionRequest, ExecutionResult
from eap.runtime.strategies import (
    ExecutionStrategy,
    IterativeStrategy,
    MultiAgentStrategy,
    SingleAgentStrategy,
    WorkflowStrategy,
)
from eap.specifications.envelope import ResourceKind
from eap.specifications.resolved_definition import ResolvedDefinition


class ExecutionCoordinator:
    def __init__(
        self,
        services: RuntimeServices,
        strategies: dict[str, ExecutionStrategy] | None = None,
    ) -> None:
        self._services = services
        self._strategies: dict[str, ExecutionStrategy] = strategies or {
            "single_agent": SingleAgentStrategy(),
            "workflow": WorkflowStrategy(),
            "multi_agent": MultiAgentStrategy(),
            "iterative": IterativeStrategy(),
        }

    def register_strategy(self, key: str, strategy: ExecutionStrategy) -> None:
        self._strategies[key] = strategy

    def run(self, rd: ResolvedDefinition, request: ExecutionRequest) -> ExecutionResult:
        # Immutable execution invariant.
        if not rd.verify_integrity():
            raise ExecutionError(
                "ResolvedDefinition failed integrity check; refusing to execute",
                code=ErrorCode.EXECUTION_FAILED,
            )

        run = RunRecord(
            id=request.run_id,
            target=rd.target,
            environment=rd.environment,
            resolved_hash=rd.content_hash,
            status=RunStatus.RUNNING,
            request={"query": request.query, "inputs": request.inputs},
        )
        self._services.metadata_repo.save_run(run)
        self._services.events.publish(
            DomainEvent(
                type=EventType.RUN_STARTED,
                payload={"run_id": run.id, "target": rd.target},
                correlation_id=run.id,
            )
        )

        strategy = self._select(rd)
        try:
            with self._services.telemetry.span("runtime.run", target=rd.target, strategy=strategy.name):
                ctx = self._services.context_service.build(rd, request)
                result = strategy.execute(ctx, self._services)
        except EapError as exc:
            return self._fail(run, exc.message, exc.to_dict())
        except Exception as exc:  # noqa: BLE001
            return self._fail(run, str(exc), {"code": ErrorCode.INTERNAL.value})

        self._finish(run, result)
        return result

    def _select(self, rd: ResolvedDefinition) -> ExecutionStrategy:
        if rd.root_kind == ResourceKind.AGENT:
            key = "single_agent"
        elif rd.root_kind == ResourceKind.WORKFLOW:
            key = "workflow"
        else:  # pragma: no cover - defensive
            raise ExecutionError(f"no strategy for root kind {rd.root_kind}", code=ErrorCode.STRATEGY_UNKNOWN)
        strategy = self._strategies.get(key)
        if strategy is None:
            raise ExecutionError(
                f"strategy '{key}' is not registered", code=ErrorCode.STRATEGY_UNKNOWN
            )
        return strategy

    def _finish(self, run: RunRecord, result: ExecutionResult) -> None:
        if result.status == "waiting_hitl":
            run.status = RunStatus.WAITING_HITL
            self._services.metadata_repo.save_run(run)
            return
        run.status = RunStatus.SUCCEEDED
        run.result = result.output
        self._services.metadata_repo.save_run(run)
        self._services.state_service.checkpoint(run.id, "completed", result.output)
        self._services.events.publish(
            DomainEvent(
                type=EventType.RUN_COMPLETED,
                payload={"run_id": run.id, "tokens": result.total_tokens},
                correlation_id=run.id,
            )
        )

    def _fail(self, run: RunRecord, message: str, error: dict) -> ExecutionResult:
        run.status = RunStatus.FAILED
        run.error = error
        self._services.metadata_repo.save_run(run)
        self._services.events.publish(
            DomainEvent(
                type=EventType.RUN_FAILED,
                payload={"run_id": run.id, "error": message},
                correlation_id=run.id,
            )
        )
        return ExecutionResult(run_id=run.id, status="failed", error=message)


__all__ = ["ExecutionCoordinator"]
