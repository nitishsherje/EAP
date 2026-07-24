# §20 — Observability

**Package:** `src/eap/observability/__init__.py`

| Feature | Status | Notes |
| --- | --- | --- |
| Structured logging | IMPLEMENTED | `configure_logging`, `get_logger` |
| OpenTelemetry spans | PARTIAL | `Telemetry.span` if `EAP_OTEL_ENABLED` and API import works; **no exporter/collector wiring in-repo** |
| MetricsSink | IMPLEMENTED | In-memory counters/observations |
| TokenTracker / FinOps | IMPLEMENTED | Used by ModelProvider; exposed in CLI demo |
| Correlation / run IDs | PARTIAL | `RunRecord.id`, DomainEvent `correlation_id=run.id`; not full W3C trace propagation beyond optional OTel span attrs |
| Agent/LLM/tool spans | PARTIAL | Named spans: `runtime.run`, `llm.complete`, `capability.invoke`, `knowledge.retrieve` |

## Events

`InProcessEventBus` publishes `RUN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED`, `SPEC_REGISTERED`, `AGENT_RESOLVED`, feedback events, etc. Not Kafka.
