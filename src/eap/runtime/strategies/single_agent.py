"""SingleAgentStrategy - runs one agent to completion."""

from __future__ import annotations

from eap.adapters import Message
from eap.common.errors import ExecutionError
from eap.runtime.agent_runner import run_agent
from eap.runtime.context import ExecutionContext
from eap.runtime.deps import RuntimeServices
from eap.runtime.models import ExecutionResult
from eap.runtime.strategies.base import ExecutionStrategy
from eap.security import DataClassification
from eap.specifications.agent import Agent


class SingleAgentStrategy(ExecutionStrategy):
    name = "single_agent"

    def execute(self, ctx: ExecutionContext, services: RuntimeServices) -> ExecutionResult:
        rd = ctx.rd
        request = ctx.request
        agent = rd.root_agent
        if not isinstance(agent, Agent):
            raise ExecutionError("SingleAgentStrategy requires an agent root")

        # Optional HITL gate for the most sensitive workloads.
        hitl_request_id = None
        if rd.effective_policy.data_classification == DataClassification.RESTRICTED.value:
            approval = services.hitl_service.request(
                request.run_id, reason="restricted data classification", payload={"target": rd.target}
            )
            hitl_request_id = approval.id
            if approval.status.value != "approved":
                return ExecutionResult(
                    run_id=request.run_id, status="waiting_hitl", hitl_request_id=hitl_request_id
                )

        outcome = run_agent(
            rd,
            agent,
            services,
            request,
            instructions=ctx.instructions,
            query=request.query,
            inputs=request.inputs,
        )

        # Persist to session memory.
        if request.query:
            services.memory_service.append(request.session_id, Message("user", request.query))
        services.memory_service.append(request.session_id, Message("assistant", outcome.content))

        return ExecutionResult(
            run_id=request.run_id,
            status="succeeded",
            output={
                "content": outcome.content,
                "structured": outcome.structured,
                "citations": outcome.citations,
                "schema_valid": outcome.schema_valid,
                "schema_errors": outcome.schema_errors,
                "guardrail_violations": outcome.guardrail_violations,
                "hallucination_flagged": outcome.hallucination_flagged,
                "hallucination_reason": outcome.hallucination_reason,
            },
            content=outcome.content,
            citations=outcome.citations,
            tool_calls=outcome.tool_calls,
            prompt_tokens=outcome.prompt_tokens,
            completion_tokens=outcome.completion_tokens,
            used_fallback=outcome.used_fallback,
            hitl_request_id=hitl_request_id,
        )
