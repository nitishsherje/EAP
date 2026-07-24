"""ContextService - assembles the execution context for a run.

Resolves the agent's effective instruction text (inline instructions and/or a
resolved prompt template) and exposes the request/session context the strategy and
framework need. Pure orchestration over the ResolvedDefinition; no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

from eap.runtime.models import ExecutionRequest
from eap.specifications.agent import Agent
from eap.specifications.resolved_definition import ResolvedDefinition


@dataclass
class ExecutionContext:
    rd: ResolvedDefinition
    request: ExecutionRequest
    instructions: str = ""


class ContextService:
    def build(self, rd: ResolvedDefinition, request: ExecutionRequest) -> ExecutionContext:
        instructions = ""
        agent = rd.root_agent
        if isinstance(agent, Agent):
            instructions = self._agent_instructions(rd, agent)
        return ExecutionContext(rd=rd, request=request, instructions=instructions)

    def _agent_instructions(self, rd: ResolvedDefinition, agent: Agent) -> str:
        parts: list[str] = []
        if agent.spec.instructions:
            parts.append(agent.spec.instructions.strip())
        if agent.spec.prompt:
            prompt = rd.bundle.prompts.get(rd.pin(agent.spec.prompt))
            if prompt is not None:
                parts.append(prompt.spec.template.strip())
        return "\n\n".join(p for p in parts if p)
