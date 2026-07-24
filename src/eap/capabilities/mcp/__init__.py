"""MCPClient - invokes operations exposed by enterprise MCP servers.

MCP is a protocol, not a layer. This client speaks MCP directly to existing
enterprise MCP servers; there is deliberately no extra "MCP adapter -> MCP server"
indirection unless a real enterprise transformation requires it.

MVP1 ships the interface with a minimal client. Wire a concrete MCP transport
(e.g. the official MCP SDK over stdio/HTTP) when an enterprise MCP server is in
scope. The endpoint/credentials come from the binding.
"""

from __future__ import annotations

from typing import Any

from eap.capabilities.base import ToolClient
from eap.common.errors import CapabilityError, ErrorCode
from eap.specifications.binding import CapabilityBinding
from eap.specifications.capability import Capability, Operation


class MCPClient(ToolClient):
    def __init__(self, secrets=None) -> None:  # noqa: ANN001
        self._secrets = secrets

    def invoke(
        self,
        capability: Capability,
        operation: Operation,
        inputs: dict[str, Any],
        binding: CapabilityBinding | None,
    ) -> dict[str, Any]:  # pragma: no cover - requires an MCP server
        if binding is None:
            raise CapabilityError(
                f"MCP capability {capability.metadata.name} has no binding",
                code=ErrorCode.BINDING_MISSING,
            )
        raise NotImplementedError(
            "MCPClient transport is not implemented in MVP1. Bind an enterprise MCP "
            "server and wire the MCP SDK here; endpoint/credentials come from the binding."
        )
