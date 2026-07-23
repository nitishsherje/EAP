"""ResponseService - governed response synthesis.

Applies output guardrails, performs a light output-schema check, and assembles the
final response envelope (content, structured output, citations, usage). This is the
last governance touchpoint before a result leaves the runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eap.evaluation import detect_hallucination
from eap.security import Guardrail, NoopGuardrail
from eap.specifications.resolved_definition import ResolvedDefinition


@dataclass
class GovernedResponse:
    content: str
    structured: dict[str, Any] | None = None
    citations: list[str] = field(default_factory=list)
    guardrail_violations: list[str] = field(default_factory=list)
    schema_valid: bool = True
    schema_errors: list[str] = field(default_factory=list)
    hallucination_flagged: bool = False
    hallucination_reason: str = ""


class ResponseService:
    def __init__(self, guardrail: Guardrail | None = None) -> None:
        self._guardrail = guardrail or NoopGuardrail()

    def build(
        self,
        rd: ResolvedDefinition,
        content: str,
        structured: dict[str, Any] | None,
        citations: list[str],
        output_schema_ref: str | None = None,
    ) -> GovernedResponse:
        gr = self._guardrail.check(content, rd.effective_policy.guardrails)
        signal = detect_hallucination(gr.content, citations)
        response = GovernedResponse(
            content=gr.content,
            structured=structured,
            citations=citations,
            guardrail_violations=gr.violations,
            hallucination_flagged=signal.flagged,
            hallucination_reason=signal.reason,
        )
        if output_schema_ref and structured is not None:
            self._validate_schema(rd, output_schema_ref, structured, response)
        return response

    def _validate_schema(
        self,
        rd: ResolvedDefinition,
        output_schema_ref: str,
        structured: dict[str, Any],
        response: GovernedResponse,
    ) -> None:
        schema_res = rd.bundle.output_schemas.get(rd.pin(output_schema_ref))
        if schema_res is None:
            return
        required = schema_res.spec.json_schema.get("required", [])
        missing = [key for key in required if key not in structured]
        if missing:
            response.schema_valid = False
            response.schema_errors = [f"missing required field: {k}" for k in missing]
