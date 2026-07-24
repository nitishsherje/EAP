# Documentation Foundation (Evidence Baseline)

This file records the evidence-based understanding established **before** authoring
the Core EAP Technical Architecture & Developer Documentation v1.0. It is not
aspirational architecture — it reflects the repository as inspected.

---

## 1. Repository Understanding Summary

**What this repository is.** A Python 3.11+ modular monolith (`eap` 1.0.0) that
implements a specification-driven Enterprise Agent Platform. Authors declare
agents/skills/workflows/capabilities/knowledge as YAML; a Control Plane validates,
registers, resolves, and binds them into an immutable `ResolvedDefinition`; a
Runtime executes that artifact through strategies and an agent-framework adapter
seam. Enterprise systems (LLM Gateway, Docling, Milvus, S3, DBs, MCP) are reached
only via thin adapters selected by environment bindings and `Settings`.

**What it is not (yet).** It is not a microservice mesh. It does not embed
Microsoft Agent Framework as a dependency. Real Postgres/S3/Milvus/MCP/OIDC
transports are largely stubs. Default backends are in-process fakes so the golden
path runs on a laptop.

**Primary surfaces**

| Surface | Location | Role |
| --- | --- | --- |
| Library + composition root | `src/eap/` | All layers |
| Declarative contracts | `contracts/` | Example YAML + generated JSON Schema |
| HTTP API | `eap.api_gateway.app` | FastAPI |
| CLI | `eap.api_gateway.cli` (`eap` entry point) | demo / catalog / resolve / run-agent |
| Tests | `tests/` | Spec, control plane, RD, runtime, workflow, API, evaluation |
| Deploy | `deploy/kubernetes`, `deploy/argocd`, `Dockerfile` | Single-service GitOps skeleton |
| Quality | `pyproject.toml` | ruff, mypy, import-linter, pytest |

**Golden path that actually runs (with fakes)**

`AgentSpec` (auditor-report-agent) → validate/register/publish → resolve (pin +
bind + policy + hash) → `ExecutionCoordinator` → `SingleAgentStrategy` →
`InProcessAgentFramework` → knowledge retrieve + deterministic skill →
`CapabilityManager` → `APIClient` → `FakeDoclingAdapter` → `ModelProvider` →
`FakeLLMAdapter` → governed response + run record + events + token tracking.

---

## 2. Detected Architecture

### Designed (frozen HLA) vs Current Implementation

| Layer | Designed | Current implementation |
| --- | --- | --- |
| Specs | Pydantic contracts + YAML | **IMPLEMENTED** (`src/eap/specifications/`) |
| Control Plane | Validate/register/resolve/govern | **IMPLEMENTED** (modules under `control_plane/`) |
| ResolvedDefinition | Immutable execution artifact | **PARTIALLY** — top-level frozen + integrity; nested bundle not deep-frozen |
| Runtime | Strategies + MAF mechanics | **PARTIAL** — strategies exist; **MAF replaced by `InProcessAgentFramework`** |
| Model Provider | Profile → adapter → LLM Gateway | **IMPLEMENTED** path; gateway HTTP present; default fake |
| Capability Manager | MCP / API / Native | **PARTIAL** — API+Native work; MCP raises `NotImplementedError` |
| Knowledge | Strategy/rerank/cite above adapters | **PARTIAL** — service owns intelligence; hybrid/keyword thin; Milvus stub |
| Adapters | Thin transport | **PARTIAL** — fakes + some HTTP stubs; Milvus/DB/S3 real paths stubbed |
| Persistence | Postgres metadata/state, S3 artifacts | **PARTIAL** — in-memory default; Postgres/S3 classes stub |
| Security | AuthN/Z, secrets, guardrails, audit | **PARTIAL** — interfaces; AllowAll/Noop defaults; OIDC stub |
| Observability | OTel + FinOps | **PARTIAL** — optional OTel spans; logging; TokenTracker; MetricsSink |
| Evaluation | Offline/online/feedback | **PARTIAL** — offline suite + hallucination hook + FeedbackService |
| Deploy | Single EKS deployable + Argo | **IMPLEMENTED** manifests (not live-validated here) |

### Actual runtime topology (MVP1)

One process: FastAPI + Control Plane + Runtime + Providers + Capabilities +
Knowledge + Adapters. Optional Worker: **not implemented**. Redis: optional
dependency listed; **no code path uses Redis**. Kafka: **not present**
(`InProcessEventBus` only).

### Dependency direction (enforced)

Import-linter contracts in `pyproject.toml` keep:

1. Layered architecture (api → runtime → providers/capabilities/knowledge →
   control_plane → adapters → persistence → security/obs/eval → specs → common)
2. Runtime must not import Control Plane
3. Specifications must not import outer layers
4. Adapters are leaf transport

Composition root (`api_gateway`) may depend on everything.

---

## 3. Implementation Coverage Matrix

| Capability | Status | Evidence |
| --- | --- | --- |
| AgentSpec / WorkflowSpec / SkillSpec / CapabilitySpec / KnowledgeSpec | IMPLEMENTED | `specifications/*.py`, `contracts/examples/` |
| CapabilityBinding | IMPLEMENTED | `binding.py`, `bindings.dev.yaml` |
| ResolvedDefinition produce + integrity gate | IMPLEMENTED | `resolver/`, `ExecutionCoordinator.run` |
| Deep immutability of nested bundle | PARTIALLY IMPLEMENTED | `frozen=True` on RD only |
| Register / publish / deprecate lifecycle | IMPLEMENTED | `LifecycleService`, `SpecificationService` |
| Environment binding at resolve | IMPLEMENTED | Resolver + bindings keyed by env |
| Policy / governance evaluation | PARTIALLY IMPLEMENTED | `GovernanceService`; `enforce` often False |
| Single-agent execution | IMPLEMENTED | `SingleAgentStrategy`, `run_agent` |
| Workflow graph via `depends_on` topo | IMPLEMENTED | `WorkflowStrategy` |
| Parallel / fan-out / iterative / dynamic workflow execution | PLANNED / NOT IMPLEMENTED | Enum exists on `WorkflowPattern`; strategy ignores pattern for parallel/etc. |
| Nested workflow steps | PLANNED / NOT IMPLEMENTED | Raises in `WorkflowStrategy` |
| Multi-agent / iterative strategies | STUBBED | Raise `NotImplementedError` |
| Microsoft Agent Framework | PLANNED / NOT IMPLEMENTED | Seam only: `AgentFrameworkAdapter` / `InProcessAgentFramework` |
| ModelProvider invoke + fallback + retry + tokens | IMPLEMENTED | `providers/llm` |
| ModelProvider stream (gateway SSE) | STUBBED | Falls back to `complete()` |
| Capability API protocol (Docling path) | IMPLEMENTED (fake default) | `APIClient` + `FakeDoclingAdapter` / `DoclingGatewayAdapter` |
| Capability Native protocol | IMPLEMENTED | `NativeRunner` |
| Capability MCP protocol | STUBBED | `MCPClient.invoke` → `NotImplementedError` |
| Knowledge retrieve + score rerank + citations + permission filter | PARTIALLY IMPLEMENTED | `KnowledgeService`; in-memory vector corpus |
| Hybrid / keyword retrieval backends | PARTIALLY IMPLEMENTED | Logs and uses vector fallback |
| Milvus real client | STUBBED | `MilvusAdapter.search` |
| Postgres metadata/state | STUBBED | `PostgresMetadataRepository` / `PostgresStateStore` |
| S3 artifact store | STUBBED | `S3ArtifactStore` |
| HITL | PARTIALLY IMPLEMENTED | Service exists; `auto_approve=True` in assembly |
| HTTP API | IMPLEMENTED | `/health`, `/v1/catalog`, `/v1/specs`, `/v1/resolve`, `/v1/agents/run`, `/v1/feedback`, `/v1/runs/{id}` |
| Run Workflow HTTP endpoint | PLANNED / NOT IMPLEMENTED | `run_workflow` on app class; no FastAPI route |
| Run Skill first-class entry | PLANNED / NOT IMPLEMENTED | Skills only via agent/workflow |
| OTel export pipeline | PARTIALLY IMPLEMENTED | Optional API spans if `EAP_OTEL_ENABLED`; no exporter wiring in-repo |
| Offline evaluation suite | IMPLEMENTED | `evaluation.run_suite` |
| Online continuous evaluation | PLANNED / NOT IMPLEMENTED | — |
| K8s / Argo CD manifests | IMPLEMENTED | `deploy/` |
| Live AWS/EKS validation | NOT IN REPO | Manifests only |

---

## 4. Documentation Plan

### Target title

**Core Enterprise Agent Platform (EAP) — Technical Architecture & Developer Documentation, Version 1.0**

### Principles

1. Describe **actual code**, cite module/file/class/method.
2. Label every feature: IMPLEMENTED / PARTIALLY IMPLEMENTED / STUBBED / PLANNED.
3. Where HLA and code disagree, show **DESIGNED ARCHITECTURE vs CURRENT IMPLEMENTATION**.
4. Mermaid diagrams reflect current call chains (InProcess framework, not MAF).
5. Do not invent Redis/Kafka/Worker/MAF usage.

### Output tree

```
docs/
  README.md                          # §§1 overview + index + how to read status labels
  architecture/
    overview.md                      # §2 system architecture + diagrams
    repository.md                    # §3 repository architecture
    designed-vs-implemented.md       # HLA vs code
    conformance-matrix.md            # §29
    known-gaps.md                    # §30
  specifications/
    contracts.md                     # §4
    lifecycle.md                     # §5
    resolved-definition.md           # §6
  runtime/
    overview.md                      # §7
    maf-boundary.md                  # §8
    agents.md                        # §9
    workflows.md                     # §10
    skills.md                        # §11
  capabilities/
    overview.md                      # §12
    mcp.md                           # §16
  knowledge/
    overview.md                      # §15
  integrations/
    model-provider.md                # §13
    docling.md                       # §14
  api/
    reference.md                     # §24
  developer-guide/
    authoring.md                     # §25
    local-development.md             # §26
    testing.md                       # §27
  deployment/
    overview.md                      # §28
  operations/
    configuration.md                 # §17
    persistence.md                   # §18
    security.md                      # §19
    observability.md                 # §20
    evaluation.md                    # §21
    reliability.md                   # §22
    end-to-end-auditor.md            # §23
  adr/
    README.md
    0001-modular-monolith.md
    0002-resolved-definition-boundary.md
    0003-agent-framework-adapter.md
    0004-adapters-over-rebuild.md
  appendices/
    glossary.md                      # §31
    examples.md
    key-interfaces.md
```

### Generation order

1. Foundation (this file) — done
2. Architecture + specifications + runtime (core narrative)
3. Capabilities / knowledge / integrations
4. API + developer guide + deployment + operations
5. ADRs + appendices + conformance/gaps
6. Root `docs/README.md` as the document front matter for all 31 sections
