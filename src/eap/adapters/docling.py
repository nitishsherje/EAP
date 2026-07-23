"""Docling adapter - transport to the CRISIL Docling Gateway (document intelligence).

EAP does not rebuild Docling. This adapter translates an EAP APIRequest into a
Docling Gateway HTTP call and **normalizes** the response into the platform
``DocumentParseResult`` shape so raw gateway payloads never leak into skills.
"""

from __future__ import annotations

from eap.adapters.base import AdapterConfig, APIAdapter, APIRequest, APIResponse
from eap.common.errors import DocumentParsingError
from eap.documents import DocumentParseResult, DocumentSection, normalize_docling_response


def build_fake_auditor_document(document_id: str) -> DocumentParseResult:
    """Seeded Independent Auditor's Report content for local/fake mode."""
    sections = [
        DocumentSection(
            title="Independent Auditor's Report",
            text="To the Members of Example Corp.",
            page=41,
        ),
        DocumentSection(
            title="Opinion",
            text=(
                "In our opinion, the accompanying financial statements present fairly, "
                "in all material respects, the financial position of the Company."
            ),
            page=41,
        ),
        DocumentSection(
            title="Basis for Opinion",
            text=(
                "We conducted our audit in accordance with Standards on Auditing. "
                "Our responsibilities are further described in the Auditor's Responsibilities section."
            ),
            page=41,
        ),
        DocumentSection(
            title="Basis for Qualified Opinion",
            text=(
                "We were unable to observe the counting of physical inventories at year end "
                "because we were appointed after that date. Consequently, we were unable to "
                "determine whether any adjustments might have been necessary."
            ),
            page=42,
        ),
        DocumentSection(
            title="Qualified Opinion",
            text=(
                "Except for the possible effects of the matter described in the Basis for "
                "Qualified Opinion section, the financial statements present fairly…"
            ),
            page=42,
        ),
        DocumentSection(
            title="Emphasis of Matter",
            text=(
                "We draw attention to Note 12 regarding related party transactions. "
                "Our opinion is not modified in respect of this matter."
            ),
            page=43,
        ),
        DocumentSection(
            title="Key Audit Matters",
            text=(
                "Key audit matters are those matters that, in our professional judgment, "
                "were of most significance in the audit. These are not qualifications."
            ),
            page=44,
        ),
    ]
    text = "\n\n".join(f"{s.title}\n{s.text}" for s in sections)
    return DocumentParseResult(
        document_id=document_id,
        text=text,
        markdown=text,
        sections=sections,
        metadata={"source": "fake-docling", "document_type": "independent_auditor_report"},
    )


class FakeDoclingAdapter(APIAdapter):
    def __init__(self, config: AdapterConfig | None = None) -> None:
        self._config = config

    def call(self, request: APIRequest) -> APIResponse:
        path = request.path or ""
        if path.endswith("/parse") or "parse" in path:
            doc_id = str(
                request.body.get("document_id")
                or request.body.get("filename")
                or "unknown"
            )
            normalized = build_fake_auditor_document(doc_id)
            return APIResponse(status=200, body=normalized.to_dict())
        return APIResponse(status=200, body={"ok": True})


class DoclingGatewayAdapter(APIAdapter):
    def __init__(self, config: AdapterConfig) -> None:
        if not config.endpoint:
            raise DocumentParsingError("Docling gateway endpoint is required")
        self._config = config

    def _headers(self, request: APIRequest) -> dict[str, str]:
        headers = {**dict(self._config.headers), **dict(request.headers)}
        if self._config.secret:
            headers.setdefault("Authorization", f"Bearer {self._config.secret}")
        cid = request.correlation_id or self._config.correlation_id
        if cid:
            headers.setdefault("X-Correlation-ID", cid)
            headers.setdefault("X-Request-ID", cid)
        return headers

    def call(self, request: APIRequest) -> APIResponse:
        import httpx

        path = request.path or self._config.path or str(self._config.config.get("path", "/v1/parse"))
        method = (request.method or self._config.method or "POST").upper()
        try:
            with httpx.Client(
                base_url=self._config.endpoint or "",
                headers=self._headers(request),
                timeout=self._config.timeout_seconds,
                verify=self._config.verify_tls,
            ) as client:
                # Prefer JSON; multipart can be enabled via config flag later.
                if self._config.config.get("multipart") and "file" in request.body:
                    files = {"file": request.body.get("file")}
                    data = {k: v for k, v in request.body.items() if k != "file"}
                    resp = client.request(method, path, data=data, files=files, params=request.query)
                else:
                    resp = client.request(
                        method, path, json=request.body, params=request.query
                    )
                resp.raise_for_status()
                raw = resp.json()
        except DocumentParsingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DocumentParsingError(f"Docling gateway call failed: {exc}") from exc

        normalized = normalize_docling_response(raw if isinstance(raw, dict) else {"content": raw})
        return APIResponse(status=resp.status_code, body=normalized.to_dict())
