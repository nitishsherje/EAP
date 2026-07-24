"""Prompt - a reusable, versioned prompt template.

Referenced as ``prompt://<name>/<version>``. Kept declarative so prompts can be
governed, reviewed and rolled back independently of agent logic.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from eap.specifications.envelope import EapResource, ResourceKind


class PromptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template: str
    # Declared template variables (validated against skill/agent inputs at resolve).
    inputs: list[str] = Field(default_factory=list)
    description: str = ""


class Prompt(EapResource):
    expected_kind: ClassVar[ResourceKind] = ResourceKind.PROMPT

    kind: ResourceKind = ResourceKind.PROMPT
    spec: PromptSpec
