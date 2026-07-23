"""LLM adapters - transport to the CRISIL LLM Gateway.

``FakeLLMAdapter`` powers local/dev and tests. ``CrisilLLMGatewayAdapter`` is the
HTTP transport used when ``EAP_LLM_BACKEND=gateway``. Platform contracts stay
independent of the OpenAI SDK; the default mapping is OpenAI-compatible
chat/completions and is fully configurable via AdapterConfig / Settings.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from eap.adapters.base import AdapterConfig, LLMAdapter, LLMRequest, LLMResponse
from eap.common.errors import AdapterError, LLMGatewayError


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _auditor_structured_from_context(messages: list) -> dict:
    """Deterministic structured findings for fake/local golden path."""
    blob = "\n".join(m.content for m in messages)
    opinion_type = "unqualified"
    details = "Opinion section indicates financial statements present fairly."
    issues: list[dict] = []
    qualifications: list[dict] = []
    emphasis: list[dict] = []
    going_concern: list[dict] = []
    evidence: list[dict] = []

    if (
        "qualified opinion" in blob.lower()
        or "basis for qualified" in blob.lower()
        or ("unable to observe" in blob.lower() and "inventor" in blob.lower())
    ):
        opinion_type = "qualified"
        details = "Qualified opinion due to scope limitation described in Basis for Qualified Opinion."
        qualifications.append(
            {
                "issue": "Scope limitation on inventory observation",
                "severity": "high",
                "details": "Unable to observe physical inventory counts.",
            }
        )
        evidence.append(
            {
                "page": 42,
                "section": "Basis for Qualified Opinion",
                "text_reference": "We were unable to observe the counting of physical inventories.",
            }
        )
    if "emphasis of matter" in blob.lower():
        emphasis.append(
            {
                "issue": "Emphasis of Matter - related party disclosures",
                "severity": "medium",
                "details": "Emphasis paragraph draws attention to related-party note.",
            }
        )
        evidence.append(
            {
                "page": 43,
                "section": "Emphasis of Matter",
                "text_reference": "We draw attention to Note 12 regarding related party transactions.",
            }
        )
    if "material uncertainty" in blob.lower() and "going concern" in blob.lower():
        going_concern.append(
            {
                "issue": "Material uncertainty related to going concern",
                "severity": "high",
                "details": "Auditor highlights material uncertainty related to going concern.",
            }
        )

    if not evidence and "Independent Auditor" in blob:
        evidence.append(
            {
                "page": 41,
                "section": "Opinion",
                "text_reference": "In our opinion, the financial statements present fairly…",
            }
        )

    summary = (
        f"Independent auditor's report analysis complete. Opinion: {opinion_type}. "
        f"{len(qualifications)} qualification(s), {len(emphasis)} emphasis item(s), "
        f"{len(going_concern)} going-concern item(s)."
    )
    return {
        "summary": summary,
        "audit_opinion": {"type": opinion_type, "details": details},
        "issues": issues,
        "qualifications": qualifications,
        "emphasis_of_matter": emphasis,
        "going_concern": going_concern,
        "other_observations": [],
        "evidence": evidence,
    }


class FakeLLMAdapter(LLMAdapter):
    """Deterministic in-process LLM used for the walking skeleton and tests."""

    def __init__(self, config: AdapterConfig | None = None) -> None:
        self._config = config

    def complete(self, request: LLMRequest) -> LLMResponse:
        if request.structured:
            payload = _auditor_structured_from_context(request.messages)
            content = json.dumps(payload)
        else:
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
    """HTTP transport to the CRISIL LLM Gateway (configurable OpenAI-compatible default)."""

    def __init__(self, config: AdapterConfig) -> None:
        if not config.endpoint:
            raise LLMGatewayError("LLM gateway endpoint is required")
        self._config = config

    def _headers(self, correlation_id: str = "") -> dict[str, str]:
        headers = {"Content-Type": "application/json", **dict(self._config.headers)}
        if self._config.secret:
            headers.setdefault("Authorization", f"Bearer {self._config.secret}")
        cid = correlation_id or self._config.correlation_id
        if cid:
            headers.setdefault("X-Correlation-ID", cid)
            headers.setdefault("X-Request-ID", cid)
        return headers

    def _path(self) -> str:
        return (
            self._config.path
            or str(self._config.config.get("path", "/v1/chat/completions"))
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        import httpx

        model = request.deployment or str(self._config.config.get("deployment", ""))
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            **request.parameters,
        }
        if request.structured and "response_format" not in payload:
            payload["response_format"] = {"type": "json_object"}
        if request.metadata:
            payload["metadata"] = request.metadata

        method = (self._config.method or "POST").upper()
        path = self._path()
        try:
            with httpx.Client(
                base_url=self._config.endpoint or "",
                headers=self._headers(request.correlation_id),
                timeout=self._config.timeout_seconds,
                verify=self._config.verify_tls,
            ) as client:
                resp = client.request(method, path, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except AdapterError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMGatewayError(f"LLM gateway call failed: {exc}") from exc

        return self._normalize(data, fallback_model=model)

    @staticmethod
    def _normalize(data: dict, fallback_model: str) -> LLMResponse:
        # OpenAI-compatible
        if "choices" in data:
            choice = data["choices"][0]
            message = choice.get("message") or {}
            content = message.get("content") or choice.get("text") or ""
            usage = data.get("usage") or {}
            return LLMResponse(
                content=content,
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                model=str(data.get("model") or fallback_model),
                finish_reason=str(choice.get("finish_reason", "stop")),
            )
        # Generic enterprise envelopes
        content = (
            data.get("content")
            or data.get("output")
            or data.get("text")
            or json.dumps(data)
        )
        return LLMResponse(
            content=str(content),
            prompt_tokens=int((data.get("usage") or {}).get("prompt_tokens", 0)),
            completion_tokens=int((data.get("usage") or {}).get("completion_tokens", 0)),
            model=str(data.get("model") or fallback_model),
            finish_reason="stop",
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:
        # SSE omitted for MVP; single-chunk fallback keeps the contract.
        yield self.complete(request).content
