"""Platform document contracts — normalized shapes for document intelligence.

Adapters (Docling) translate enterprise-specific payloads into these contracts.
Skills consume only these shapes, never raw gateway responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentParseRequest:
    """Logical request to parse a document (no infrastructure URLs)."""

    document_id: str = ""
    filename: str = ""
    mime_type: str = "application/pdf"
    # Optional raw bytes or object-store reference — never a gateway URL.
    content_ref: str = ""
    options: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "document_id": self.document_id,
            "filename": self.filename,
            "mime_type": self.mime_type,
        }
        if self.content_ref:
            body["content_ref"] = self.content_ref
        if self.options:
            body["options"] = self.options
        if self.metadata:
            body["metadata"] = self.metadata
        return body


@dataclass
class DocumentSection:
    title: str
    text: str
    page: int | None = None


@dataclass
class DocumentParseResult:
    """Stable EAP document view — safe for skills/business logic."""

    document_id: str = ""
    text: str = ""
    markdown: str = ""
    sections: list[DocumentSection] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    pages: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "text": self.text,
            "markdown": self.markdown,
            "sections": [
                {"title": s.title, "text": s.text, "page": s.page} for s in self.sections
            ],
            "tables": self.tables,
            "pages": self.pages,
            "metadata": self.metadata,
            "artifacts": self.artifacts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentParseResult:
        sections = [
            DocumentSection(
                title=str(s.get("title", "")),
                text=str(s.get("text", s.get("content", ""))),
                page=s.get("page"),
            )
            for s in data.get("sections") or []
            if isinstance(s, dict)
        ]
        text = str(data.get("text") or data.get("content") or "")
        if not text and sections:
            text = "\n\n".join(f"{s.title}\n{s.text}" for s in sections)
        return cls(
            document_id=str(data.get("document_id", "")),
            text=text,
            markdown=str(data.get("markdown") or data.get("md") or ""),
            sections=sections,
            tables=list(data.get("tables") or []),
            pages=list(data.get("pages") or []),
            metadata=dict(data.get("metadata") or {}),
            artifacts=list(data.get("artifacts") or []),
        )


def normalize_docling_response(body: dict[str, Any]) -> DocumentParseResult:
    """Map enterprise Docling (or fake) payloads into DocumentParseResult.

    Accepts several common shapes so gateway quirks stay in the adapter layer.
    """
    if not isinstance(body, dict):
        return DocumentParseResult(text=str(body))

    # Already normalized
    if "sections" in body or "text" in body or "content" in body:
        return DocumentParseResult.from_dict(body)

    # Nested envelopes: { "result": {...} } / { "document": {...} }
    for key in ("result", "document", "data", "output"):
        nested = body.get(key)
        if isinstance(nested, dict):
            return DocumentParseResult.from_dict(nested)

    return DocumentParseResult.from_dict(body)


__all__ = [
    "DocumentParseRequest",
    "DocumentParseResult",
    "DocumentSection",
    "normalize_docling_response",
]
