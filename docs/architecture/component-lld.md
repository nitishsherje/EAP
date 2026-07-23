# Core EAP v1.0 — Component Low-Level Design (Phase 3)

> **Note:** For implementation-accurate status labels (IMPLEMENTED / STUBBED /
> etc.) and designed-vs-current callouts, prefer the v1.0 doc set starting at
> [`../README.md`](../README.md). This LLD may still speak in HLA terms (e.g. MAF)
> where the code uses stand-ins.

This document details each component: responsibility, key types,
collaborators, and the invariants it upholds. Cross-check against `src/eap/`
before treating any claim as live behavior.

## Layering & dependency rule

Inner-to-outer only; enforced in CI by `import-linter` (see `pyproject.toml`).

```
api_gateway (6)  composition root
runtime (5)      ExecutionCoordinator, strategies, MAF adapter
providers|capabilities|knowledge (4)
control_plane (2)
adapters (3, leaf transport)
persistence (1)
security|observability|evaluation (1)
specifications (0)
common (0)
```

Two hard rules beyond the layering: **Runtime never imports Control Plane**, and
**Specifications is pure domain**. Control Plane and Runtime communicate only
through the persisted `ResolvedDefinition`.

---

## 1. Specification Layer (`eap.specifications`)

| Component | Responsibility | Key types |
| --- | --- | --- |
| `envelope` | Canonical resource envelope + kind enforcement | `EapResource`, `Metadata`, `ResourceKind` |
| `references` | Logical reference grammar `<scheme>://<name>[/<version>]` | `Reference`, `Scheme` |
| `versioning` | SemVer parse/compare/select, compatibility | `SemVer`, `select_version`, `Compatibility` |
| Contracts | Typed specs | `Agent`, `Workflow`, `Skill`, `Capability`, `Knowledge` |
| Supporting | Governed resources | `ModelProfile`, `Prompt`, `Policy`, `OutputSchema`, `CapabilityBinding` |
| `resolved_definition` | Immutable execution artifact | `ResolvedDefinition`, `ResolvedBundle`, `EffectivePolicy` |
| `loader` | YAML/dict -> typed model dispatch, structured errors | `parse_resource`, `load_file` |

Invariants: every reference is well-formed and scheme-correct at parse time
(field validators); every resource has a valid SemVer; `extra="forbid"` keeps
specs strict.

## 2. Control Plane (`eap.control_plane`)

| Module | Responsibility | Collaborators |
| --- | --- | --- |
| `spec_service` | schema/semantic/reference/compatibility validation, ingest | `Registry` |
| `registry` | immutable versioned storage, reference→version resolution, aliases | `MetadataRepository` |
| `catalog` | read/query views | `Registry` |
| `resolver` | **produces `ResolvedDefinition`** (walk graph, pin versions, bind env, apply policy, hash) | `Registry`, `GovernanceService` |
| `lifecycle` | publish/deprecate/promote with valid transitions, events | `MetadataRepository`, `EventPublisher` |
| `governance` | RBAC/ABAC evaluation, classification, effective policy | `AuditLogger`, `Principal` |

The `Resolver` is the single producer of the ResolvedDefinition boundary. It
requires published resources by default, requires an environment binding for
every capability/knowledge/model (native capabilities excepted), recurses model
fallback chains, and finalizes with a SHA-256 content hash.

## 3. ResolvedDefinition boundary (`eap.specifications.resolved_definition`)

Immutable (`frozen=True`) artifact carrying the pinned `ResolvedBundle`, the
`EffectivePolicy`, `Provenance`, and a `content_hash`. `resolution_map` maps each
reference-as-written to its pinned form so the runtime never re-resolves. The
runtime refuses to execute unless `verify_integrity()` passes.

## 4. Runtime (`eap.runtime`)

| Component | Responsibility |
| --- | --- |
| `ExecutionCoordinator` | verify integrity → record run → build context → select strategy → govern result → emit events |
| `framework.AgentFrameworkAdapter` | **MAF isolation seam**; `InProcessAgentFramework` is the MVP1 default |
| `strategies.SingleAgentStrategy` | run one agent (via shared `agent_runner`) |
| `strategies.WorkflowStrategy` | topological multi-step (skill + agent steps), placeholder resolution |
| `strategies.{MultiAgent,Iterative}Strategy` | stubs behind the interface |
| `ContextService` | assemble instructions (inline + resolved prompt) |
| `MemoryService` | session memory |
| `StateCheckpointService` | resumable checkpoints via `StateStore` |
| `HITLService` | approval gate + events |
| `ResponseService` | guardrails, output-schema check, hallucination hook, citations |

Strategy selection is by `ResolvedDefinition.root_kind`. Agent mechanics are
delegated to the framework adapter; the model, capability and knowledge services
are injected as invokers, mirroring how a MAF-backed adapter would receive model
and tool clients.

## 5. Model Provider (`eap.providers.llm`)

`ModelProvider.invoke(rd, model_ref, messages, structured, tenant)` resolves the
`ModelProfile` + binding from the RD, builds the LLM adapter, applies
retry/backoff + circuit breaker, routes through the fallback chain, parses
structured output, and records `TokenUsage` (FinOps). `stream()` provides token
streaming.

## 6. Capability Manager (`eap.capabilities`)

`CapabilityManager.invoke(rd, capability_ref, operation, inputs)` routes by
protocol to a `ToolClient`: `APIClient` (Docling/enterprise APIs via API adapter),
`NativeRunner` (in-process governed functions), or `MCPClient` (enterprise MCP
servers; interface + minimal client). Normalizes results and records telemetry.

## 7. Knowledge Service (`eap.knowledge`)

`KnowledgeService.retrieve(rd, knowledge_ref, query, principal)` performs query
planning, backend search (vector adapter), permission filtering by data
classification, pluggable reranking, and citation assembly. Agents reference
`knowledge://` only.

## 8. Adapters (`eap.adapters`)

Thin transport: `llm_gateway`, `docling`, `milvus`, `storage`, `enterprise_api`,
`database`. Each has a fake/in-memory implementation for local/dev and a real
implementation (or documented stub). Config/credentials injected via
`AdapterConfig`; the resolved secret value is supplied by the composition root
from the binding's `secret_ref` through the `SecretsProvider`.

## 9. Persistence (`eap.persistence`)

`MetadataRepository`, `ArtifactStore`, `StateStore` interfaces with in-memory
defaults and PostgreSQL/S3 stubs selected by `Settings`.

## 10. Cross-cutting (`eap.security`, `eap.observability`, `eap.evaluation`, `eap.common`)

Security (authn, secrets, guardrails, audit, classification), observability
(telemetry spans, metrics, `TokenTracker`), evaluation (evaluators, regression
harness, hallucination hook, feedback capture), events (`InProcessEventBus`), and
reliability (retry, circuit breaker).
