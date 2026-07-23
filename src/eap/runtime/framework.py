"""AgentFrameworkAdapter - execution-engine port (MAF-ready).

EAP owns specifications, resolution, governance and capability/knowledge
abstraction. Agent *mechanics* are delegated through this port so Microsoft
Agent Framework (or any engine) can be swapped without leaking framework types
into the EAP domain.

CURRENT IMPLEMENTATION:
  ``InProcessAgentFramework`` — deterministic local engine for tests/fake mode.
PLANNED:
  ``MafAgentFramework`` — maps AgentInvocation → MAF agent + tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field

from eap.adapters import Message
from eap.capabilities import CapabilityResult
from eap.knowledge import RetrievalResult
from eap.providers.llm import ModelResult
from eap.runtime.models import ToolCall
from eap.runtime.skill_context import SkillContext, SkillHandlerRegistry
from eap.specifications.skill import Skill, SkillType

ModelInvoker = Callable[[list[Message], bool], ModelResult]
ToolInvoker = Callable[[str, str, dict], CapabilityResult]
KnowledgeInvoker = Callable[[str, str], RetrievalResult]


@dataclass
class Invokers:
    model: ModelInvoker
    tool: ToolInvoker
    retrieve: KnowledgeInvoker


@dataclass
class AgentInvocation:
    instructions: str
    query: str
    model_ref: str
    inputs: dict = field(default_factory=dict)
    knowledge_refs: list[str] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    output_schema_ref: str | None = None
    max_iterations: int = 6
    history: list[Message] = field(default_factory=list)
    correlation_id: str = ""
    run_id: str = ""


@dataclass
class FrameworkResult:
    content: str
    structured: dict | None = None
    citations: list[str] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    used_fallback: bool = False


class AgentFrameworkAdapter(ABC):
    """Port for agent execution engines (InProcess / future MAF)."""

    @abstractmethod
    def run_agent(self, invocation: AgentInvocation, invokers: Invokers) -> FrameworkResult: ...


class InProcessAgentFramework(AgentFrameworkAdapter):
    """Deterministic in-process agent loop (local/fake stand-in for MAF)."""

    def __init__(self, skill_handlers: SkillHandlerRegistry | None = None) -> None:
        self._skill_handlers = skill_handlers or SkillHandlerRegistry()

    def run_agent(self, invocation: AgentInvocation, invokers: Invokers) -> FrameworkResult:
        context_blocks: list[str] = []
        citations: list[str] = []
        tool_calls: list[ToolCall] = []
        skill_structured: dict | None = None
        prompt_tokens = completion_tokens = 0
        used_fallback = False

        for know_ref in invocation.knowledge_refs:
            result = invokers.retrieve(know_ref, invocation.query or invocation.instructions)
            for chunk in result.chunks[:3]:
                context_blocks.append(f"[knowledge:{chunk.source or chunk.id}] {chunk.text}")
            citations.extend(result.citations)

        for skill in invocation.skills:
            if skill.spec.type == SkillType.FUNCTION:
                handler = self._skill_handlers.get(skill.metadata.name)
                if handler is None:
                    continue

                def recording_tool(ref: str, op: str, inputs: dict, _skill=skill) -> CapabilityResult:
                    result = invokers.tool(ref, op, inputs)
                    tool_calls.append(
                        ToolCall(
                            capability=result.capability,
                            operation=result.operation,
                            ok=result.ok,
                            summary=str(result.output)[:200] if result.ok else (result.error or ""),
                        )
                    )
                    return result

                def recording_model(messages: list[Message], structured: bool) -> ModelResult:
                    nonlocal prompt_tokens, completion_tokens, used_fallback
                    result = invokers.model(messages, structured)
                    prompt_tokens += result.prompt_tokens
                    completion_tokens += result.completion_tokens
                    used_fallback = used_fallback or result.used_fallback
                    return result

                ctx = SkillContext(
                    skill_name=skill.metadata.name,
                    inputs=dict(invocation.inputs),
                    query=invocation.query,
                    instructions=invocation.instructions,
                    model_ref=invocation.model_ref,
                    correlation_id=invocation.correlation_id or invocation.run_id,
                    invoke_capability=recording_tool,
                    reason=recording_model,
                )
                output = handler(ctx)
                tool_calls.append(
                    ToolCall(
                        capability=f"skill://{skill.metadata.name}",
                        operation="run",
                        ok=isinstance(output, dict),
                        summary=str((output or {}).get("summary", output))[:200],
                    )
                )
                if isinstance(output, dict):
                    skill_structured = output
                    context_blocks.append(
                        f"[skill:{skill.metadata.name}] {output.get('summary', output)}"
                    )
                continue

            if skill.spec.type != SkillType.DETERMINISTIC:
                continue
            for use in skill.spec.capabilities:
                if not use.operation:
                    continue
                cap_result = invokers.tool(use.ref, use.operation, invocation.inputs)
                tool_calls.append(
                    ToolCall(
                        capability=cap_result.capability,
                        operation=cap_result.operation,
                        ok=cap_result.ok,
                        summary=str(cap_result.output)[:200] if cap_result.ok else (cap_result.error or ""),
                    )
                )
                if cap_result.ok:
                    context_blocks.append(
                        f"[skill:{skill.metadata.name}/{use.operation}] {cap_result.output}"
                    )

        # FUNCTION skills that already produced structured findings are authoritative.
        if skill_structured and "summary" in skill_structured:
            deduped = list(dict.fromkeys(citations))
            return FrameworkResult(
                content=str(skill_structured.get("summary", "")),
                structured=skill_structured,
                citations=deduped,
                tool_calls=tool_calls,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                used_fallback=used_fallback,
            )

        system_parts = [invocation.instructions] if invocation.instructions else []
        if context_blocks:
            system_parts.append("Context:\n" + "\n".join(context_blocks))
        messages: list[Message] = []
        if system_parts:
            messages.append(Message(role="system", content="\n\n".join(system_parts)))
        messages.extend(invocation.history)
        messages.append(Message(role="user", content=invocation.query or "Proceed with the task."))

        want_structured = invocation.output_schema_ref is not None
        model_result = invokers.model(messages, want_structured)
        deduped = list(dict.fromkeys(citations))
        return FrameworkResult(
            content=model_result.content,
            structured=model_result.structured,
            citations=deduped,
            tool_calls=tool_calls,
            prompt_tokens=model_result.prompt_tokens,
            completion_tokens=model_result.completion_tokens,
            used_fallback=model_result.used_fallback,
        )
