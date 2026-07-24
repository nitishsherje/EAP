"""Skill execution context — platform abstractions only (no adapters).

FUNCTION skills receive a SkillContext and may invoke capabilities / models
through injected callables. Skills must never import Docling/LLM adapters.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from eap.adapters import Message
from eap.capabilities import CapabilityResult
from eap.providers.llm import ModelResult

CapabilityInvoker = Callable[[str, str, dict[str, Any]], CapabilityResult]
ModelInvoker = Callable[[list[Message], bool], ModelResult]
SkillHandler = Callable[["SkillContext"], dict[str, Any]]


@dataclass
class SkillContext:
    skill_name: str
    inputs: dict[str, Any]
    query: str
    instructions: str = ""
    model_ref: str = ""
    correlation_id: str = ""
    invoke_capability: CapabilityInvoker | None = None
    reason: ModelInvoker | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def capabilities_invoke(self, capability_ref: str, operation: str, inputs: dict | None = None) -> CapabilityResult:
        if self.invoke_capability is None:
            raise RuntimeError("capability invoker not bound")
        return self.invoke_capability(capability_ref, operation, inputs if inputs is not None else self.inputs)

    def models_reason(self, messages: list[Message], structured: bool = False) -> ModelResult:
        if self.reason is None:
            raise RuntimeError("model invoker not bound")
        return self.reason(messages, structured)


class SkillHandlerRegistry:
    """Maps skill metadata.name -> handler. Not a control-plane registry."""

    def __init__(self) -> None:
        self._handlers: dict[str, SkillHandler] = {}

    def register(self, skill_name: str, handler: SkillHandler) -> None:
        self._handlers[skill_name] = handler

    def get(self, skill_name: str) -> SkillHandler | None:
        return self._handlers.get(skill_name)


__all__ = ["SkillContext", "SkillHandler", "SkillHandlerRegistry"]
