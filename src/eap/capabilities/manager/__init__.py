"""CapabilityManager - routes capability operations to the right ToolClient.

Responsibilities: tool discovery, protocol routing (mcp/api/native), invocation,
result normalization, and per-invocation guardrails. Resolves the capability and
its binding from the ResolvedDefinition, never from raw specs.
"""

from __future__ import annotations

from typing import Any

from eap.capabilities.api import APIClient
from eap.capabilities.base import CapabilityResult, ToolClient
from eap.capabilities.mcp import MCPClient
from eap.capabilities.native import NativeRunner, NativeToolRegistry
from eap.common.config import Settings
from eap.common.errors import CapabilityError, ErrorCode
from eap.observability import Telemetry, get_logger
from eap.security import Guardrail, NoopGuardrail, SecretsProvider
from eap.specifications.capability import Protocol
from eap.specifications.resolved_definition import ResolvedDefinition

_log = get_logger("eap.capabilities")


class CapabilityManager:
    def __init__(
        self,
        settings: Settings,
        secrets: SecretsProvider,
        guardrail: Guardrail | None = None,
        telemetry: Telemetry | None = None,
        native_registry: NativeToolRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._guardrail = guardrail or NoopGuardrail()
        self._telemetry = telemetry or Telemetry()
        self._native = NativeRunner(native_registry)
        self._clients: dict[Protocol, ToolClient] = {
            Protocol.API: APIClient(settings, secrets),
            Protocol.NATIVE: self._native,
            Protocol.MCP: MCPClient(secrets),
        }

    @property
    def native_registry(self) -> NativeToolRegistry:
        return self._native.registry

    def discover(self, rd: ResolvedDefinition, capability_ref: str) -> list[str]:
        capability = rd.bundle.capabilities.get(rd.pin(capability_ref))
        if capability is None:
            return []
        return [op.name for op in capability.spec.operations]

    def invoke(
        self,
        rd: ResolvedDefinition,
        capability_ref: str,
        operation_name: str,
        inputs: dict[str, Any],
    ) -> CapabilityResult:
        pinned = rd.pin(capability_ref)
        capability = rd.bundle.capabilities.get(pinned)
        if capability is None:
            raise CapabilityError(f"capability {pinned} not in resolved definition")
        operation = capability.spec.operation(operation_name)
        if operation is None:
            raise CapabilityError(
                f"operation {operation_name!r} not found on {pinned}",
                code=ErrorCode.OPERATION_UNKNOWN,
            )

        client = self._clients[capability.spec.protocol]
        binding = rd.binding_for(capability_ref)

        with self._telemetry.span(
            "capability.invoke", capability=capability.metadata.name, operation=operation_name
        ):
            try:
                output = client.invoke(capability, operation, inputs, binding)
            except NotImplementedError as exc:
                return CapabilityResult(
                    capability=pinned, operation=operation_name, error=str(exc)
                )

        return CapabilityResult(capability=pinned, operation=operation_name, output=output)


__all__ = ["CapabilityManager", "CapabilityResult", "NativeToolRegistry"]
