"""Runtime data types (Layer 5 internal)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eap.common.ids import new_id
from eap.security import Principal


@dataclass
class ExecutionRequest:
    """A request to execute a ResolvedDefinition."""

    inputs: dict[str, Any] = field(default_factory=dict)
    query: str = ""
    principal: Principal = field(default_factory=Principal.system)
    environment: str = "dev"
    session_id: str = field(default_factory=lambda: new_id("sess"))
    run_id: str = field(default_factory=lambda: new_id("run"))
    resume_from: str | None = None  # checkpoint name to resume from


@dataclass
class ToolCall:
    capability: str
    operation: str
    ok: bool
    summary: str = ""


@dataclass
class ExecutionResult:
    run_id: str
    status: str  # succeeded | failed | waiting_hitl
    output: dict[str, Any] = field(default_factory=dict)
    content: str = ""
    citations: list[str] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    used_fallback: bool = False
    error: str | None = None
    hitl_request_id: str | None = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
