"""Model Provider - governed LLM invocation.

Distinct from the Capability Manager: model invocation has its own concerns
(streaming, token accounting, model routing, structured output, context windows,
fallback, model telemetry). The LLM is NOT treated as just another tool.

Flow:
    ModelProfile (pinned)  ->  binding  ->  LLM adapter  ->  CRISIL LLM Gateway

The provider resolves the profile/binding from the ResolvedDefinition, so it never
touches raw specs or the control plane.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from eap.adapters import LLMRequest, Message, build_llm_adapter
from eap.common.config import Settings
from eap.common.errors import ProviderError
from eap.common.reliability import CircuitBreaker, RetryPolicy, retry_call
from eap.observability import Telemetry, TokenTracker, TokenUsage, get_logger
from eap.security import SecretsProvider
from eap.specifications.resolved_definition import ResolvedDefinition

_log = get_logger("eap.providers.llm")


@dataclass
class ModelResult:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    structured: dict[str, Any] | None = None
    used_fallback: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ModelProvider:
    settings: Settings
    secrets: SecretsProvider
    token_tracker: TokenTracker = field(default_factory=TokenTracker)
    telemetry: Telemetry = field(default_factory=Telemetry)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    # Rough per-1k-token cost estimate for FinOps demos (override per model in prod).
    cost_per_1k_tokens: float = 0.0

    def __post_init__(self) -> None:
        self._breaker = CircuitBreaker()

    def invoke(
        self,
        rd: ResolvedDefinition,
        model_ref: str,
        messages: list[Message],
        *,
        structured: bool | None = None,
        tenant: str = "default",
    ) -> ModelResult:
        """Invoke a model with routing + fallback. Records token usage."""
        chain = self._routing_chain(rd, model_ref)
        last_error: Exception | None = None
        for index, pinned in enumerate(chain):
            try:
                result = self._invoke_one(rd, pinned, messages, structured, tenant)
                result.used_fallback = index > 0
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                _log.warning("model %s failed (%s); trying next in chain", pinned, exc)
        raise ProviderError(f"all models in routing chain failed: {last_error}")

    def stream(
        self,
        rd: ResolvedDefinition,
        model_ref: str,
        messages: list[Message],
        *,
        tenant: str = "default",
    ) -> Iterator[str]:
        pinned = rd.pin(model_ref)
        adapter, deployment, params = self._prepare(rd, pinned)
        request = LLMRequest(deployment=deployment, messages=messages, parameters=params)
        yield from adapter.stream(request)

    # --- internals ---
    def _routing_chain(self, rd: ResolvedDefinition, model_ref: str) -> list[str]:
        pinned = rd.pin(model_ref)
        profile = rd.bundle.models.get(pinned)
        chain = [pinned]
        if profile:
            chain.extend(rd.pin(fb) for fb in profile.spec.fallback)
        return chain

    def _prepare(self, rd: ResolvedDefinition, pinned: str):
        profile = rd.bundle.models.get(pinned)
        if profile is None:
            raise ProviderError(f"model profile {pinned} not present in resolved definition")
        binding = rd.binding_for(pinned)
        if binding is None:
            raise ProviderError(f"no binding for model {pinned}")
        adapter = build_llm_adapter(binding, self.secrets, self.settings)
        deployment = binding.spec.config.get("deployment", profile.spec.model)
        params = profile.spec.parameters.model_dump(exclude_none=True)
        return adapter, deployment, params

    def _invoke_one(
        self,
        rd: ResolvedDefinition,
        pinned: str,
        messages: list[Message],
        structured: bool | None,
        tenant: str,
    ) -> ModelResult:
        profile = rd.bundle.models.get(pinned)
        adapter, deployment, params = self._prepare(rd, pinned)
        want_structured = structured if structured is not None else (
            profile.spec.structured_output if profile else False
        )
        request = LLMRequest(
            deployment=deployment,
            messages=messages,
            parameters=params,
            structured=want_structured,
        )

        with self.telemetry.span("llm.complete", model=deployment):
            response = self._breaker.call(
                lambda: retry_call(lambda: adapter.complete(request), self.retry_policy)
            )

        usage = TokenUsage(
            model=deployment,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cost_usd=self._estimate_cost(response.prompt_tokens + response.completion_tokens),
            tenant=tenant,
        )
        self.token_tracker.record(usage)

        structured_out = self._maybe_parse(response.content) if want_structured else None
        return ModelResult(
            content=response.content,
            model=response.model or deployment,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            structured=structured_out,
        )

    def _estimate_cost(self, tokens: int) -> float:
        return round((tokens / 1000.0) * self.cost_per_1k_tokens, 6)

    @staticmethod
    def _maybe_parse(content: str) -> dict[str, Any] | None:
        text = content.strip()
        if not (text.startswith("{") and text.endswith("}")):
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


__all__ = ["ModelProvider", "ModelResult"]
