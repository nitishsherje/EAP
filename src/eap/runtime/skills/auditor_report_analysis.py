"""Auditor report analysis skill — domain logic only.

Uses platform abstractions (capability invoke + model reason). Never imports
Docling/LLM adapters or enterprise URLs.
"""

from __future__ import annotations

from typing import Any

from eap.adapters import Message
from eap.documents import DocumentParseResult, normalize_docling_response
from eap.runtime.skill_context import SkillContext

DOCUMENT_CAPABILITY = "capability://document-intelligence/1.0.0"
PARSE_OPERATION = "parse_document"

AUDITOR_SECTION_HINTS = (
    "independent auditor",
    "opinion",
    "basis for opinion",
    "qualified opinion",
    "basis for qualified",
    "adverse opinion",
    "disclaimer of opinion",
    "emphasis of matter",
    "material uncertainty",
    "going concern",
    "other matter",
)


def _select_auditor_sections(doc: DocumentParseResult) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for section in doc.sections:
        title_l = section.title.lower()
        if any(h in title_l for h in AUDITOR_SECTION_HINTS):
            if "key audit matter" in title_l:
                continue
            selected.append({"title": section.title, "text": section.text, "page": section.page})
    if not selected and doc.text:
        selected.append({"title": "Document", "text": doc.text[:4000], "page": None})
    return selected


def _empty_findings(summary: str) -> dict[str, Any]:
    return {
        "summary": summary,
        "audit_opinion": {"type": "unknown", "details": "Insufficient evidence to classify opinion."},
        "issues": [],
        "qualifications": [],
        "emphasis_of_matter": [],
        "going_concern": [],
        "other_observations": [],
        "evidence": [],
    }


def run(ctx: SkillContext) -> dict[str, Any]:
    """Parse document → select auditor sections → reason → structured findings."""
    parse_result = ctx.capabilities_invoke(DOCUMENT_CAPABILITY, PARSE_OPERATION, ctx.inputs)
    if not parse_result.ok:
        return _empty_findings(f"Document parse failed: {parse_result.error or 'unknown error'}")

    doc = normalize_docling_response(parse_result.output if isinstance(parse_result.output, dict) else {})
    sections = _select_auditor_sections(doc)
    context_text = "\n\n".join(
        f"## {s['title']} (page={s.get('page')})\n{s['text']}" for s in sections
    )

    system = (
        "You are an Independent Auditor's Report analyst. "
        "Extract audit opinion, qualifications, emphasis of matter, and going-concern "
        "uncertainties. Do NOT treat Key Audit Matters as qualifications. "
        "Do not invent findings without textual evidence. "
        "Return JSON with keys: summary, audit_opinion, issues, qualifications, "
        "emphasis_of_matter, going_concern, other_observations, evidence."
    )
    user = (
        f"Query: {ctx.query or 'Analyze the independent auditor report.'}\n\n"
        f"Document id: {doc.document_id or ctx.inputs.get('document_id', '')}\n\n"
        f"Relevant sections:\n{context_text}"
    )
    model_result = ctx.models_reason(
        [Message(role="system", content=system), Message(role="user", content=user)],
        True,
    )
    structured = model_result.structured
    if isinstance(structured, dict) and "summary" in structured:
        structured.setdefault("evidence", [])
        if not structured["evidence"] and sections:
            structured["evidence"] = [
                {
                    "page": s.get("page"),
                    "section": s.get("title"),
                    "text_reference": str(s.get("text", ""))[:240],
                }
                for s in sections[:3]
            ]
        return structured

    return _empty_findings(
        "Model did not return structured findings; evidence sections were identified "
        f"({len(sections)} section(s)) but classification is unavailable."
    )


__all__ = ["DOCUMENT_CAPABILITY", "PARSE_OPERATION", "run"]
