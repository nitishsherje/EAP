# DESIGNED ARCHITECTURE vs CURRENT IMPLEMENTATION

This page is the canonical disagreement log between the frozen HLA / blueprint and
the repository as implemented.

| Concern | DESIGNED ARCHITECTURE | CURRENT IMPLEMENTATION | Status |
| --- | --- | --- | --- |
| Deployable units | Single API/Runtime; optional Worker | Single process only; no Worker | PARTIAL |
| Agent mechanics | Microsoft Agent Framework | `InProcessAgentFramework` deterministic loop | GAP |
| Multi-agent / iterative | MAF primitives via strategies | Strategies raise `NotImplementedError` | STUBBED |
| Workflow patterns | sequential, parallel, graph, fan-out, iterative, dynamic | Spec enum has all; **runtime executes topo-order graph only** (sequential if no deps) | PARTIAL |
| Spec purity | pydantic only | Specs also import `eap.common` | MINOR DRIFT |
| Persistence | PostgreSQL + S3 | In-memory default; Postgres/S3 stubs | STUBBED |
| Redis | Optional if justified | Listed in optional deps; **unused in code** | NOT USED |
| Eventing | In-process MVP; Kafka later | `InProcessEventBus` only | AS DESIGNED (MVP) |
| MCP | One of three protocols | Interface + NotImplementedError | STUBBED |
| Auth | Enterprise IAM/SSO | `AllowAllAuthenticator` default; OIDC stub | PARTIAL |
| Guardrails | Per capability invocation + response | Response path uses Noop; CapabilityManager never calls guardrail | GAP |
| HITL | Approval/resume | Present; `auto_approve=True` in assembly | PARTIAL |
| Run Workflow HTTP | Implied by runtime API | `EapApplication.run_workflow` exists; **no FastAPI route** | PARTIAL |
| Run Skill entry | Mentioned in reviews | Skills only via agent/workflow steps | NOT IMPLEMENTED |

See also: [conformance-matrix.md](conformance-matrix.md), [known-gaps.md](known-gaps.md).
