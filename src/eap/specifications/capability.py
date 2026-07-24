"""CapabilitySpec - a logical technical/business capability.

A capability exposes one or more *operations* (tools). It is invoked through the
Capability Manager via one of three protocols (mcp | api | native). The physical
endpoint/credentials/adapter are supplied by a CapabilityBinding, never here.

    capability://document-intelligence/1.0.0
        operations: [parse_document, extract_tables, ...]
"""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from eap.specifications.envelope import EapResource, ResourceKind


class CapabilityType(str, Enum):
    TOOL = "tool"
    KNOWLEDGE = "knowledge"
    SERVICE = "service"
    STORAGE = "storage"


class Protocol(str, Enum):
    """How the Capability Manager reaches the operation."""

    MCP = "mcp"
    API = "api"
    NATIVE = "native"


class Operation(BaseModel):
    """A single callable operation (tool) exposed by the capability."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9_]*$")
    description: str = ""
    # Inline JSON Schema or a schema:// reference string.
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    # API-protocol hints (ignored for mcp/native).
    method: str | None = None
    path: str | None = None
    # Whether results should be coerced to structured output.
    structured: bool = False


class CapabilitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: CapabilityType = CapabilityType.TOOL
    protocol: Protocol = Protocol.API
    operations: list[Operation] = Field(..., min_length=1)
    required_scopes: list[str] = Field(default_factory=list)
    classification: str = "internal"
    data_sensitivity: str = "internal"

    def operation(self, name: str) -> Operation | None:
        return next((op for op in self.operations if op.name == name), None)


class Capability(EapResource):
    expected_kind: ClassVar[ResourceKind] = ResourceKind.CAPABILITY

    kind: ResourceKind = ResourceKind.CAPABILITY
    spec: CapabilitySpec
