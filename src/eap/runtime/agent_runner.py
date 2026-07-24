"""Shared agent execution helper.

Runs a single agent from the ResolvedDefinition bundle by building the framework
invocation + invokers and delegating mechanics to the AgentFrameworkAdapter. Used
by both SingleAgentStrategy and WorkflowStrategy (for agent steps).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eap.runtime.deps import RuntimeServices
from eap.runtime.framework import AgentInvocation, Invokers
from eap.runtime.models import ExecutionRequest, ToolCall
from eap.specifications.agent import Agent
from eap.specifications.resolved_definition import ResolvedDefinition


@dataclass
class AgentOutcome:
    content: str
    structured: dict[str, Any] | None = None
    citations: list[str] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    used_fallback: bool = False
    schema_valid: bool = True
    schema_errors: list[str] = field(default_factory=list)
    guardrail_violations: list[str] = field(default_factory=list)
    hallucination_flagged: bool = False
    hallucination_reason: str = ""


def build_invokers(
    rd: ResolvedDefinition, agent: Agent, services: RuntimeServices, request: ExecutionRequest
) -> Invokers:
    correlation_id = request.run_id

    def model_invoker(messages, structured):
        return services.model_provider.invoke(
            rd,
            agent.spec.model,
            messages,
            structured=structured,
            tenant=request.principal.tenant,
            correlation_id=correlation_id,
        )

    def tool_invoker(cap_ref, operation, inputs):
        return services.capability_manager.invoke(
            rd, cap_ref, operation, inputs, correlation_id=correlation_id
        )

    def knowledge_invoker(knowledge_ref, query):
        return services.knowledge_service.retrieve(rd, knowledge_ref, query, request.principal)

    return Invokers(model=model_invoker, tool=tool_invoker, retrieve=knowledge_invoker)


def run_agent(
    rd: ResolvedDefinition,
    agent: Agent,
    services: RuntimeServices,
    request: ExecutionRequest,
    instructions: str,
    query: str,
    inputs: dict[str, Any],
) -> AgentOutcome:
    invokers = build_invokers(rd, agent, services, request)
    skills = [
        rd.bundle.skills[rd.pin(s)] for s in agent.spec.skills if rd.pin(s) in rd.bundle.skills
    ]
    history = services.memory_service.history(
        request.session_id, agent.spec.memory.scope, agent.spec.memory.max_turns
    )
    invocation = AgentInvocation(
        instructions=instructions,
        query=query,
        model_ref=agent.spec.model,
        inputs=inputs,
        knowledge_refs=list(agent.spec.knowledge),
        skills=skills,
        capabilities=list(agent.spec.capabilities),
        output_schema_ref=agent.spec.output_schema,
        max_iterations=agent.spec.max_iterations,
        history=history,
        correlation_id=request.run_id,
        run_id=request.run_id,
    )
    result = services.framework.run_agent(invocation, invokers)
    response = services.response_service.build(
        rd,
        content=result.content,
        structured=result.structured,
        citations=result.citations,
        output_schema_ref=agent.spec.output_schema,
    )
    return AgentOutcome(
        content=response.content,
        structured=response.structured,
        citations=response.citations,
        tool_calls=result.tool_calls,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        used_fallback=result.used_fallback,
        schema_valid=response.schema_valid,
        schema_errors=response.schema_errors,
        guardrail_violations=response.guardrail_violations,
        hallucination_flagged=response.hallucination_flagged,
        hallucination_reason=response.hallucination_reason,
    )
