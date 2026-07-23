# Core Enterprise Agent Platform (EAP)

## Technical Architecture & Developer Documentation

**Version:** 1.0  
**Scope:** Actual implementation in this repository (walking-skeleton MVP1)  
**Audience:** Platform engineers, agent authors, reviewers, operators

---

### How to read status labels

| Label | Meaning |
| --- | --- |
| **IMPLEMENTED** | Present, exercised by code paths and/or tests |
| **PARTIALLY IMPLEMENTED** | Structure exists; behavior incomplete or defaulted to no-ops/fakes |
| **STUBBED** | Class/method exists but raises `NotImplementedError` or is a placeholder |
| **PLANNED / NOT IMPLEMENTED** | Mentioned in design comments/enums only; no working path |

Where the frozen HLA and code disagree, documents use:

- **DESIGNED ARCHITECTURE** — frozen baseline intent  
- **CURRENT IMPLEMENTATION** — what the repository actually does

Evidence baseline used to author this set: [`_meta/documentation-foundation.md`](_meta/documentation-foundation.md).

---

## 1. Executive Overview

### What EAP is

Core EAP is a **specification-driven, governed agent execution platform** implemented as a **single-process modular monolith** (`src/eap/`). Authors declare agents, skills, workflows, capabilities, knowledge, model profiles, policies, and bindings as versioned YAML. The Control Plane validates and resolves them into an immutable **`ResolvedDefinition`**. The Runtime executes only that artifact.

EAP does **not** rebuild enterprise LLM hosting, document intelligence, vector search, or object storage. It integrates existing CRISIL capabilities through **adapters** selected by environment **CapabilityBindings**.

### Problems it solves

| Problem | Approach in this repo |
| --- | --- |
| Agents defined as ad-hoc code | Portable YAML contracts + Pydantic models |
| Execution from mutable YAML | Forbidden on public path; only integrity-verified `ResolvedDefinition` runs |
| Infra details leaking into agent specs | Logical refs (`capability://…`) + env bindings |
| Mixing LLM and tools as one concern | Separate **Model Provider** and **Capability Manager** |
| Uncontrolled dependency direction | import-linter contracts in CI |

### Core design philosophy

```
Contracts define WHAT
  → Control Plane validates, versions, resolves, governs
  → ResolvedDefinition defines exactly WHAT executes
  → Runtime determines HOW it executes
  → AgentFrameworkAdapter provides agent-loop mechanics
  → Model Provider / Capability Manager / Knowledge Service invoke enterprise capabilities
  → Adapters integrate existing backends
```

### Specification-driven architecture

Every registrable resource uses the envelope:

```yaml
apiVersion: eap.crisil/v1
kind: Agent | Workflow | Skill | …
metadata: { name, version, … }
spec: { … }
```

Executable form: `src/eap/specifications/`. Declarative artifacts: `contracts/`.

### Relationship with existing enterprise capabilities

| Enterprise system | EAP role | Status |
| --- | --- | --- |
| CRISIL LLM Gateway | `CrisilLLMGatewayAdapter` | PARTIALLY — HTTP client present; default **fake** |
| Docling Gateway | `DoclingGatewayAdapter` | PARTIALLY — HTTP client present; default **fake** |
| Milvus | `MilvusAdapter` | STUBBED (in-memory vector used by default) |
| PostgreSQL | metadata/state repos | STUBBED (in-memory default) |
| S3 | artifact / object storage | STUBBED (in-memory default) |
| MCP servers | `MCPClient` | STUBBED |
| Microsoft Agent Framework | Designed owner of agent mechanics | **NOT INTEGRATED** — `InProcessAgentFramework` stand-in |

---

## Document map (sections 2–31)

| § | Topic | Document |
| --- | --- | --- |
| 2 | System Architecture | [architecture/overview.md](architecture/overview.md) |
| 3 | Repository Architecture | [architecture/repository.md](architecture/repository.md) |
| 4 | Specification Contract | [specifications/contracts.md](specifications/contracts.md) |
| 5 | Specification Lifecycle | [specifications/lifecycle.md](specifications/lifecycle.md) |
| 6 | ResolvedDefinition | [specifications/resolved-definition.md](specifications/resolved-definition.md) |
| 7 | Runtime | [runtime/overview.md](runtime/overview.md) |
| 8 | MAF Integration | [runtime/maf-boundary.md](runtime/maf-boundary.md) |
| 9 | Agents | [runtime/agents.md](runtime/agents.md) |
| 10 | Workflows | [runtime/workflows.md](runtime/workflows.md) |
| 11 | Skills | [runtime/skills.md](runtime/skills.md) |
| 12 | Capabilities | [capabilities/overview.md](capabilities/overview.md) |
| 13 | Model Provider | [integrations/model-provider.md](integrations/model-provider.md) |
| 14 | Docling | [integrations/docling.md](integrations/docling.md) |
| 15 | Knowledge | [knowledge/overview.md](knowledge/overview.md) |
| 16 | MCP | [capabilities/mcp.md](capabilities/mcp.md) |
| 17 | Configuration & Binding | [operations/configuration.md](operations/configuration.md) |
| 18 | Persistence | [operations/persistence.md](operations/persistence.md) |
| 19 | Security & Governance | [operations/security.md](operations/security.md) |
| 20 | Observability | [operations/observability.md](operations/observability.md) |
| 21 | Evaluation | [operations/evaluation.md](operations/evaluation.md) |
| 22 | Reliability | [operations/reliability.md](operations/reliability.md) |
| 23 | End-to-End Auditor | [operations/end-to-end-auditor.md](operations/end-to-end-auditor.md) |
| 24 | API Reference | [api/reference.md](api/reference.md) |
| 25 | Developer Guide | [developer-guide/authoring.md](developer-guide/authoring.md) |
| 26 | Local Development | [developer-guide/local-development.md](developer-guide/local-development.md) |
| 27 | Testing | [developer-guide/testing.md](developer-guide/testing.md) |
| 28 | Deployment | [deployment/overview.md](deployment/overview.md) |
| 29 | Conformance Matrix | [architecture/conformance-matrix.md](architecture/conformance-matrix.md) |
| 30 | Known Gaps | [architecture/known-gaps.md](architecture/known-gaps.md) |
| 31 | Appendices | [appendices/glossary.md](appendices/glossary.md) |

Also: [architecture/designed-vs-implemented.md](architecture/designed-vs-implemented.md) · [adr/](adr/)
