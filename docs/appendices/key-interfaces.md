# Appendix — Key interfaces & classes

| Layer | Symbol | Module |
| --- | --- | --- |
| Specs | `EapResource`, `ResolvedDefinition` | `eap.specifications` |
| Control | `ControlPlane`, `Resolver`, `SpecificationService`, `Registry` | `eap.control_plane` |
| Runtime | `ExecutionCoordinator`, `ExecutionStrategy`, `AgentFrameworkAdapter` | `eap.runtime` |
| Framework | `InProcessAgentFramework`, `Invokers` | `eap.runtime.framework` |
| Model | `ModelProvider`, `ModelResult` | `eap.providers.llm` |
| Caps | `CapabilityManager`, `ToolClient`, `APIClient`, `NativeRunner`, `MCPClient` | `eap.capabilities` |
| Knowledge | `KnowledgeService`, `Reranker` | `eap.knowledge` |
| Adapters | `LLMAdapter`, `APIAdapter`, `VectorStoreAdapter`, factories | `eap.adapters` |
| Persist | `MetadataRepository`, `ArtifactStore`, `StateStore` | `eap.persistence` |
| Security | `Authenticator`, `SecretsProvider`, `Guardrail`, `AuditLogger` | `eap.security` |
| Obs | `Telemetry`, `TokenTracker` | `eap.observability` |
| Eval | `Evaluator`, `run_suite`, `FeedbackService` | `eap.evaluation` |
| App | `EapApplication` | `eap.api_gateway.assembly` |

## Architecture Decision summary

1. Modular monolith (ADR 0001)  
2. ResolvedDefinition boundary (ADR 0002)  
3. Framework adapter seam; MAF pending (ADR 0003)  
4. Adapters over rebuild (ADR 0004)  
