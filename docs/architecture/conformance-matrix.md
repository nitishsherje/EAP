# §29 — Architecture Conformance Matrix

| Architecture Requirement | Status | Repository Evidence | Gap | Recommendation |
| --- | --- | --- | --- | --- |
| Specification envelope + core kinds | IMPLEMENTED | `specifications/*`, `contracts/` | Spec imports `common` | Accept for MVP |
| Logical refs + SemVer | IMPLEMENTED | `references.py`, `versioning.py` | — | — |
| Control Plane validate/register/resolve | IMPLEMENTED | `control_plane/` | Dangling refs at ingest weak | Optional preflight |
| ResolvedDefinition integrity gate | PARTIAL | `Resolver`, `ExecutionCoordinator.run` | Shallow freeze; strategies/`run_resolved` can skip full CP pipeline | Deep-freeze; seal lower entry points |
| Runtime ↛ Control Plane | IMPLEMENTED | import-linter + code | — | Keep contract |
| MAF owns agent mechanics | NOT IMPLEMENTED | `InProcessAgentFramework` | Home-grown loop | MAF adapter |
| ModelProvider ≠ MCP tool | IMPLEMENTED | `providers/llm` | Gateway SSE stub | Complete streaming |
| Capability MCP/API/Native | PARTIAL | `capabilities/` | MCP stub; unused guardrail | Implement MCP; apply guardrail |
| Docling via binding | IMPLEMENTED (fake default) | skill→API→docling adapter | Live gateway untested | Integration env |
| Knowledge above Milvus | PARTIAL | `knowledge/`, `milvus.py` | Hybrid thin; Milvus stub | Real pymilvus |
| No Kafka/Redis required | IMPLEMENTED (absent) | InProcessEventBus | — | Keep until justified |
| Single deployable | IMPLEMENTED | Dockerfile + K8s | — | — |
| AuthN/Z enterprise | STUBBED/PARTIAL | AllowAll, OIDC stub | Permissive defaults | Wire SSO; enforce policies |
| Offline evaluation | IMPLEMENTED | `evaluation/` | Online eval missing | Add when needed |
| Tests prove invariants | PARTIAL | `tests/` | Secrets/retry/audit gaps | Expand suite |
