"""Docling adapter - transport to the CRISIL Docling Gateway (document intelligence).

EAP does not rebuild Docling. This adapter only translates an EAP APIRequest into
a Docling Gateway HTTP call. ``FakeDoclingAdapter`` powers local/dev.
"""

from __future__ import annotations

from eap.adapters.base import AdapterConfig, APIAdapter, APIRequest, APIResponse
from eap.common.errors import AdapterError


class FakeDoclingAdapter(APIAdapter):
    def __init__(self, config: AdapterConfig | None = None) -> None:
        self._config = config

    def call(self, request: APIRequest) -> APIResponse:
        if request.path.endswith("/parse"):
            doc_id = request.body.get("document_id", "unknown")
            return APIResponse(
                status=200,
                body={
                    "document_id": doc_id,
                    "content": f"[fake-docling] parsed content for {doc_id}",
                    "sections": [
                        {"title": "Audit Findings", "text": "No material misstatements identified."},
                        {"title": "Notes", "text": "Refer to schedule 3 for details."},
                    ],
                },
            )
        return APIResponse(status=200, body={"ok": True})


class DoclingGatewayAdapter(APIAdapter):
    def __init__(self, config: AdapterConfig) -> None:
        if not config.endpoint:
            raise AdapterError("Docling gateway endpoint is required")
        self._config = config

    def call(self, request: APIRequest) -> APIResponse:  # pragma: no cover - needs gateway
        import httpx

        headers = {}
        if self._config.secret:
            headers["Authorization"] = f"Bearer {self._config.secret}"
        try:
            with httpx.Client(
                base_url=self._config.endpoint or "",
                headers=headers,
                timeout=self._config.timeout_seconds,
            ) as client:
                resp = client.request(
                    request.method, request.path, json=request.body, params=request.query
                )
                resp.raise_for_status()
                return APIResponse(status=resp.status_code, body=resp.json())
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(f"Docling gateway call failed: {exc}") from exc
