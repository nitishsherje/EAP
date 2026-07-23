"""LLM adapters - transport to the CRISIL LLM Gateway.

``FakeLLMAdapter`` powers local/dev and tests. ``CrisilLLMGatewayAdapter`` is the
real HTTP transport (OpenAI-compatible chat/completions style) used when
``EAP_LLM_BACKEND=gateway``. The gateway performs model hosting; EAP only adapts.
"""

from __future__ import annotations

from collections.abc import Iterator

from eap.adapters.base import AdapterConfig, LLMAdapter, LLMRequest, LLMResponse
from eap.common.errors import AdapterError


def _estimate_tokens(text: str) -> int:
    # Rough heuristic used only by the fake adapter for FinOps demos.
    return max(1, len(text) // 4)


class FakeLLMAdapter(LLMAdapter):
    """Deterministic in-process LLM used for the walking skeleton and tests."""

    def __init__(self, config: AdapterConfig | None = None) -> None:
        self._config = config

    def complete(self, request: LLMRequest) -> LLMResponse:
        last_user = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        content = (
            "[fake-llm] Based on the provided context, here is a structured analysis. "
            f"(deployment={request.deployment}) Summary of request: {last_user[:160]}"
        )
        prompt_tokens = sum(_estimate_tokens(m.content) for m in request.messages)
        return LLMResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=_estimate_tokens(content),
            model=request.deployment,
            finish_reason="stop",
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:
        for token in self.complete(request).content.split(" "):
            yield token + " "


class CrisilLLMGatewayAdapter(LLMAdapter):
    """HTTP transport to the CRISIL LLM Gateway (chat/completions style)."""

    def __init__(self, config: AdapterConfig) -> None:
        if not config.endpoint:
            raise AdapterError("LLM gateway endpoint is required", code=None)
        self._config = config

    def _client(self):
        import httpx

        headers = {}
        if self._config.secret:
            headers["Authorization"] = f"Bearer {self._config.secret}"
        return httpx.Client(
            base_url=self._config.endpoint,
            headers=headers,
            timeout=self._config.timeout_seconds,
        )

    def complete(self, request: LLMRequest) -> LLMResponse:  # pragma: no cover - needs gateway
        payload = {
            "model": request.deployment,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            **request.parameters,
        }
        try:
            with self._client() as client:
                resp = client.post("/v1/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(f"LLM gateway call failed: {exc}") from exc
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            model=data.get("model", request.deployment),
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:  # pragma: no cover - needs gateway
        # SSE streaming omitted from MVP1; fall back to a single chunk.
        yield self.complete(request).content
