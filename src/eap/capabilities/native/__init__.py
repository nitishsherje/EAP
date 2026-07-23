"""NativeRunner - invokes in-process governed functions.

Native tools are Python callables registered under (capability_name, operation).
They run inside the platform (no external transport) but are still governed by the
same capability contract, scopes and guardrails.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from eap.capabilities.base import ToolClient
from eap.common.errors import EapError, ErrorCode
from eap.specifications.binding import CapabilityBinding
from eap.specifications.capability import Capability, Operation

NativeFunction = Callable[[dict[str, Any]], dict[str, Any]]


class NativeToolRegistry:
    def __init__(self) -> None:
        self._fns: dict[tuple[str, str], NativeFunction] = {}

    def register(self, capability_name: str, operation: str, fn: NativeFunction) -> None:
        self._fns[(capability_name, operation)] = fn

    def get(self, capability_name: str, operation: str) -> NativeFunction | None:
        return self._fns.get((capability_name, operation))


class NativeRunner(ToolClient):
    def __init__(self, registry: NativeToolRegistry | None = None) -> None:
        self._registry = registry or NativeToolRegistry()

    @property
    def registry(self) -> NativeToolRegistry:
        return self._registry

    def invoke(
        self,
        capability: Capability,
        operation: Operation,
        inputs: dict[str, Any],
        binding: CapabilityBinding | None,
    ) -> dict[str, Any]:
        fn = self._registry.get(capability.metadata.name, operation.name)
        if fn is None:
            raise EapError(
                f"no native function registered for {capability.metadata.name}.{operation.name}",
                code=ErrorCode.OPERATION_UNKNOWN,
            )
        return fn(inputs)
