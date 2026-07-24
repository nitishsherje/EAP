"""OutputSchema - a governed contract for structured output.

Referenced as ``schema://<name>/<version>``. Wraps a JSON Schema document that
agents/skills must conform their output to. Enables output validation and
downstream contract stability.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from eap.specifications.envelope import EapResource, ResourceKind


class OutputSchemaSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # A JSON Schema object describing the expected output shape.
    json_schema: dict[str, Any] = Field(..., alias="schema")


class OutputSchema(EapResource):
    expected_kind: ClassVar[ResourceKind] = ResourceKind.OUTPUT_SCHEMA

    kind: ResourceKind = ResourceKind.OUTPUT_SCHEMA
    spec: OutputSchemaSpec
