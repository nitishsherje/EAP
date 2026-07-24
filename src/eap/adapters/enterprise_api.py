"""Generic enterprise API adapter - transport to internal APIs/microservices.

Used by capabilities whose protocol is ``api`` and whose binding adapter is
``enterprise_api``. Thin HTTP passthrough; fake returns an echo for local/dev.
"""

from __future__ import annotations

from eap.adapters.base import AdapterConfig, APIAdapter, APIRequest, APIResponse
from eap.common.errors import AdapterError


class FakeEnterpriseAPIAdapter(APIAdapter):
    def __init__(self, config: AdapterConfig | None = None) -> None:
        self._config = config

    def call(self, request: APIRequest) -> APIResponse:
        return APIResponse(
            status=200,
            body={"echo": {"method": request.method, "path": request.path, "body": request.body}},
        )


class EnterpriseAPIAdapter(APIAdapter):
    def __init__(self, config: AdapterConfig) -> None:
        if not config.endpoint:
            raise AdapterError("enterprise API endpoint is required")
        self._config = config

    def call(self, request: APIRequest) -> APIResponse:  # pragma: no cover - needs backend
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
            raise AdapterError(f"enterprise API call failed: {exc}") from exc
