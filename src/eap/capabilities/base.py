"""Capability Manager shared types.

A capability exposes operations (tools). The Capability Manager routes an
operation to one of three ToolClients based on the capability protocol:
    mcp    -> MCPClient    -> Enterprise MCP Servers
    api    -> APIClient    -> API Adapter -> APIs / Docling / Microservices
    native -> NativeRunner -> local governed functions
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from eap.specifications.binding import CapabilityBinding
from eap.specifications.capability import Capability, Operation


@dataclass
class CapabilityResult:
    capability: str
    operation: str
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class ToolClient(ABC):
    """Transport-family client that actually invokes an operation."""

    @abstractmethod
    def invoke(
        self,
        capability: Capability,
        operation: Operation,
        inputs: dict[str, Any],
        binding: CapabilityBinding | None,
    ) -> dict[str, Any]: ...
