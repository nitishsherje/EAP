# §19 — Security & Governance

| Concern | Status | Evidence |
| --- | --- | --- |
| Authentication | PARTIAL | `AllowAllAuthenticator` default; `BearerTokenAuthenticator` STUB |
| Authorization (RBAC/ABAC) | PARTIAL | `GovernanceService.authorize`; enforce often off |
| Secrets | PARTIAL | `EnvSecretsProvider`; enterprise SM not wired |
| Policy resources | IMPLEMENTED | `Policy` / `PolicySpec`; loaded into RD |
| Policy enforcement | PARTIAL | Depends on `enforce_policies` / `EAP_AUTH_ENABLED` |
| Audit logging | PARTIAL | `LoggingAuditLogger` |
| Guardrails | PARTIAL | `NoopGuardrail`; CapabilityManager does not call; ResponseService uses injected guardrail |
| PII / data protection | PLANNED | Classification enums exist; no PII redaction engine |
| HITL | PARTIAL | Auto-approve in assembly |

## Principal

`security.Principal` — subject, roles, tenant, attributes. System principal used heavily in tests/CLI.

## API auth

FastAPI extracts `Authorization` bearer token → `application.authenticate`. With AllowAll, any token → system; none → anonymous.
