# §3 — Repository Architecture

## 3.1 Tree (implementation-relevant)

```
EAP/
├── contracts/                 # Declarative YAML + JSON Schema
│   ├── examples/              # Agent, Skill, Capability, Knowledge, Workflow, bindings
│   ├── model_profiles/
│   ├── policies/
│   ├── output_schemas/
│   └── schemas/               # Generated from Pydantic
├── src/eap/
│   ├── common/                # Layer 0 utilities
│   ├── specifications/        # Layer 0 contracts (executable)
│   ├── security/              # Layer 1
│   ├── observability/
│   ├── evaluation/
│   ├── persistence/           # Interfaces + memory + stubs
│   ├── control_plane/         # Layer 2
│   ├── adapters/              # Layer 3
│   ├── providers/llm/         # Layer 4
│   ├── capabilities/          # Layer 4
│   ├── knowledge/             # Layer 4
│   ├── runtime/               # Layer 5
│   └── api_gateway/           # Layer 6 composition root
├── tests/
├── scripts/generate_schemas.py
├── deploy/kubernetes/         # Kustomize base + overlays
├── deploy/argocd/
├── Dockerfile
├── pyproject.toml
└── docs/                      # This documentation set
```

## 3.2 Package catalog

For each package: **WHAT / WHY / RESPONSIBILITY / KEY CLASSES / DEPENDENCIES / WHO CALLS IT**.

### `eap.common`

| | |
| --- | --- |
| WHAT | Errors, IDs, events, Settings, reliability primitives |
| WHY | Shared Layer-0 utilities without business logic |
| KEY | `Settings`, `EapError`, `InProcessEventBus`, `RetryPolicy`, `CircuitBreaker` |
| DEPS | stdlib only (+ typing) |
| CALLED BY | Nearly all packages |

### `eap.specifications`

| | |
| --- | --- |
| WHAT | Pydantic resource models, loader, SemVer, references, ResolvedDefinition |
| WHY | Single typed source of truth for contracts |
| KEY | `Agent`, `Workflow`, `Skill`, `Capability`, `Knowledge`, `CapabilityBinding`, `ResolvedDefinition`, `load_file`, `Reference`, `SemVer` |
| DEPS | pydantic, pyyaml, `eap.common` (errors/ids) |
| CALLED BY | control_plane, runtime, providers, capabilities, knowledge, api_gateway |

### `eap.security`

| | |
| --- | --- |
| WHAT | Principal, Authenticator, SecretsProvider, Guardrail, AuditLogger |
| WHY | Injectable security seams |
| KEY | `AllowAllAuthenticator`, `EnvSecretsProvider`, `NoopGuardrail`, `LoggingAuditLogger`, `BearerTokenAuthenticator` (STUB) |
| DEPS | common |
| CALLED BY | api_gateway, control_plane governance, providers/capabilities factories |

### `eap.observability`

| | |
| --- | --- |
| WHAT | Logging, Telemetry spans, MetricsSink, TokenTracker |
| WHY | Cross-cutting observability / FinOps |
| KEY | `Telemetry`, `TokenTracker`, `configure_logging` |
| DEPS | logging; optional opentelemetry-api |
| CALLED BY | assembly, providers, capabilities, knowledge, runtime |

### `eap.evaluation`

| | |
| --- | --- |
| WHAT | Offline evaluators, hallucination heuristic, FeedbackService |
| WHY | Quality hooks decoupled from runtime imports |
| KEY | `run_suite`, `detect_hallucination`, `FeedbackService` |
| DEPS | common.events |
| CALLED BY | api_gateway (feedback), response path (hallucination), tests |

### `eap.persistence`

| | |
| --- | --- |
| WHAT | MetadataRepository, ArtifactStore, StateStore + factories |
| WHY | Persist registry/runs/artifacts/checkpoints |
| KEY | `InMemory*`, `Postgres*` (STUB), `S3ArtifactStore` (STUB), `build_*` |
| DEPS | common, specifications (via models) |
| CALLED BY | control_plane, runtime, assembly |

### `eap.control_plane`

| | |
| --- | --- |
| WHAT | Spec service, registry, catalog, resolver, lifecycle, governance |
| WHY | Governed path from authoring to ResolvedDefinition |
| KEY | `ControlPlane`, `Resolver`, `SpecificationService`, `Registry` |
| DEPS | specifications, persistence, security, common |
| CALLED BY | api_gateway only (runtime must not import) |

### `eap.adapters`

| | |
| --- | --- |
| WHAT | LLM, Docling, Milvus, storage, database, enterprise API transports |
| WHY | Leaf integration; no business logic |
| KEY | `FakeLLMAdapter`, `CrisilLLMGatewayAdapter`, `FakeDoclingAdapter`, `DoclingGatewayAdapter`, `InMemoryVectorAdapter`, `MilvusAdapter` (STUB), factories in `__init__.py` |
| DEPS | common, binding config via AdapterConfig |
| CALLED BY | providers, capabilities.api, knowledge |

### `eap.providers.llm`

| | |
| --- | --- |
| WHAT | ModelProvider |
| WHY | LLM concerns ≠ tools |
| KEY | `ModelProvider.invoke`, `.stream`, `_routing_chain` |
| DEPS | adapters, specifications (RD), observability, reliability, security |
| CALLED BY | runtime `build_invokers` |

### `eap.capabilities`

| | |
| --- | --- |
| WHAT | CapabilityManager + API/Native/MCP ToolClients |
| WHY | Protocol routing for capability operations |
| KEY | `CapabilityManager`, `APIClient`, `NativeRunner`, `MCPClient` (STUB) |
| DEPS | adapters, specifications |
| CALLED BY | runtime invokers |

### `eap.knowledge`

| | |
| --- | --- |
| WHAT | KnowledgeService + ScoreReranker |
| WHY | Retrieval intelligence above vector backends |
| KEY | `KnowledgeService.retrieve` |
| DEPS | adapters.vector, specifications |
| CALLED BY | runtime invokers |

### `eap.runtime`

| | |
| --- | --- |
| WHAT | Coordinator, strategies, framework adapter, context/memory/state/hitl/response |
| WHY | Execute ResolvedDefinition |
| KEY | `ExecutionCoordinator`, `SingleAgentStrategy`, `WorkflowStrategy`, `InProcessAgentFramework`, `run_agent` |
| DEPS | providers, capabilities, knowledge, persistence, specs(RD) — **never** control_plane |
| CALLED BY | api_gateway |

### `eap.api_gateway`

| | |
| --- | --- |
| WHAT | Composition root, FastAPI, CLI |
| WHY | Only place allowed to wire all layers |
| KEY | `EapApplication`, `build_app_with_examples`, FastAPI routes, CLI commands |
| DEPS | everything |
| CALLED BY | uvicorn, `eap` console script, tests |

## 3.3 contracts/ vs specifications/

| Path | Role |
| --- | --- |
| `contracts/` | Human/CI declarative artifacts (YAML examples, JSON Schema) |
| `src/eap/specifications/` | Executable validation & typed models |

Schema generation: `scripts/generate_schemas.py` (CI checks drift).
