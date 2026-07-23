"""APIClient - invokes API-protocol operations via an API adapter.

Maps an EAP Operation + inputs onto an HTTP call and returns the normalized body.
The concrete adapter (Docling, enterprise API) is chosen from the binding.
"""

from __future__ import annotations

from typing import Any

from eap.adapters import APIRequest, build_api_adapter
from eap.capabilities.base import ToolClient
from eap.common.config import Settings
from eap.common.errors import CapabilityError, ErrorCode
from eap.common.reliability import RetryPolicy, retry_call
from eap.security import SecretsProvider
from eap.specifications.binding import CapabilityBinding
from eap.specifications.capability import Capability, Operation


class APIClient(ToolClient):
    def __init__(self, settings: Settings, secrets: SecretsProvider) -> None:
        self._settings = settings
        self._secrets = secrets

    def invoke(
        self,
        capability: Capability,
        operation: Operation,
        inputs: dict[str, Any],
        binding: CapabilityBinding | None,
    ) -> dict[str, Any]:
        if binding is None:
            raise CapabilityError(
                f"API capability {capability.metadata.name} has no binding",
                code=ErrorCode.BINDING_MISSING,
            )
        adapter = build_api_adapter(binding, self._secrets, self._settings)
        request = APIRequest(
            method=(operation.method or "POST").upper(),
            path=operation.path or f"/{operation.name}",
            body=inputs,
        )
        policy = RetryPolicy(max_attempts=binding.spec.max_retries + 1)
        response = retry_call(lambda: adapter.call(request), policy)
        if response.status >= 400:
            raise CapabilityError(
                f"operation {operation.name} failed with status {response.status}",
                code=ErrorCode.ADAPTER_ERROR,
            )
        return response.body
