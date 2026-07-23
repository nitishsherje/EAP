"""Observability & FinOps (Layer 1, cross-cutting).

Thin wrappers over OpenTelemetry (optional) plus structured logging, a metrics
sink, and token/cost tracking. Designed so the platform is fully observable by
default without forcing an OTel collector in local/dev.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


class Telemetry:
    """Span factory. Uses OTel when enabled/available, otherwise a no-op."""

    def __init__(self, enabled: bool = False, service_name: str = "eap") -> None:
        self._tracer = None
        if enabled:
            try:  # pragma: no cover - optional dependency path
                from opentelemetry import trace

                self._tracer = trace.get_tracer(service_name)
            except Exception:  # noqa: BLE001
                self._tracer = None

    @contextmanager
    def span(self, name: str, **attributes) -> Iterator[None]:
        if self._tracer is None:
            yield
            return
        with self._tracer.start_as_current_span(name) as span:  # pragma: no cover
            for key, value in attributes.items():
                span.set_attribute(key, value)
            yield


@dataclass
class MetricsSink:
    """Minimal in-memory metrics registry (counter + gauge/observation)."""

    counters: dict[str, float] = field(default_factory=dict)
    observations: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str, value: float = 1.0, **labels) -> None:
        key = _label_key(name, labels)
        self.counters[key] = self.counters.get(key, 0.0) + value

    def observe(self, name: str, value: float, **labels) -> None:
        key = _label_key(name, labels)
        self.observations.setdefault(key, []).append(value)


def _label_key(name: str, labels: dict) -> str:
    if not labels:
        return name
    tags = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return f"{name}{{{tags}}}"


@dataclass
class TokenUsage:
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    tenant: str = "default"

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class TokenTracker:
    """FinOps: aggregates token usage and cost per model/tenant."""

    def __init__(self, metrics: MetricsSink | None = None) -> None:
        self._records: list[TokenUsage] = []
        self._metrics = metrics or MetricsSink()

    def record(self, usage: TokenUsage) -> None:
        self._records.append(usage)
        self._metrics.increment(
            "eap_tokens_total", usage.total_tokens, model=usage.model, tenant=usage.tenant
        )
        self._metrics.increment(
            "eap_cost_usd_total", usage.cost_usd, model=usage.model, tenant=usage.tenant
        )

    def total_tokens(self, tenant: str | None = None) -> int:
        rows = self._records if tenant is None else [r for r in self._records if r.tenant == tenant]
        return sum(r.total_tokens for r in rows)

    def total_cost(self, tenant: str | None = None) -> float:
        rows = self._records if tenant is None else [r for r in self._records if r.tenant == tenant]
        return round(sum(r.cost_usd for r in rows), 6)


__all__ = [
    "MetricsSink",
    "Telemetry",
    "TokenTracker",
    "TokenUsage",
    "configure_logging",
    "get_logger",
]
