# §22 — Error Handling & Reliability

**Package:** `eap.common.reliability`

| Mechanism | Status | Where used |
| --- | --- | --- |
| Retry + exponential backoff | IMPLEMENTED | `retry_call` — ModelProvider, APIClient |
| Circuit breaker | IMPLEMENTED | ModelProvider around complete |
| Timeouts | PARTIAL | Binding `timeout_seconds` passed into httpx clients |
| Model fallback | IMPLEMENTED | ModelProfile `fallback` list |
| Capability failure | PARTIAL | Workflow continues per-step; skill collects ok/error ToolCalls; no compensate path |
| Idempotency helpers | PLANNED | Comment in reliability module only |
| Checkpoint / resume | PARTIAL | Checkpoints saved on success; HITL waiting status exists; full resume orchestration limited |
| Structured errors | IMPLEMENTED | `EapError` + `ErrorCode` mapped to HTTP in `app.py` |

`WorkflowSpec.on_error` (`fail|continue|compensate`) is stored on the spec; **WorkflowStrategy does not implement compensate**.
