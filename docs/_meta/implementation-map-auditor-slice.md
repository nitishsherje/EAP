# Phase 0 — Implementation map (internal)

## Existing abstractions (REUSE)

| Responsibility | Location | Action |
| --- | --- | --- |
| Spec registry | `control_plane.registry.Registry` | Keep |
| Resolve + bind + policy | `control_plane.resolver.Resolver` | Keep |
| ResolvedDefinition | `specifications.resolved_definition` | Keep |
| Execution entry | `runtime.execution.ExecutionCoordinator` | Keep |
| MAF seam | `runtime.framework.AgentFrameworkAdapter` + `InProcessAgentFramework` | Keep; clarify as port |
| Capability dispatch | `capabilities.manager.CapabilityManager` | Keep |
| LLM | `providers.llm.ModelProvider` + `adapters.llm_gateway` | Strengthen |
| Docling | `adapters.docling` via APIClient | Strengthen + normalize |
| Native functions | `capabilities.native.NativeToolRegistry` | Reuse for skill helpers if needed |
| Secrets | `security.EnvSecretsProvider` | Extend env alias support |
| Settings | `common.config.Settings` | Extend gateway config fields |

## Baseline status

- `framework.py` present; `deps.py` import valid
- pytest: **31 collected, 31 passed**
- Canonical naming: hyphenated (`auditor-report-agent.yaml`) — fix README underscore typo only

## Gaps to close (this slice)

1. Document parse contracts + Docling response normalization
2. Configurable LLM/Docling gateway (URL/path/headers/timeout/correlation)
3. FUNCTION skill runner for auditor-report-analysis (uses invokers only)
4. Structured auditor findings schema + fake LLM/Docling fixtures
5. Focused tests + README path fix

## Will NOT create

CapabilityRegistry, ModelResolver, AgentRuntime, second control plane, RAG/Milvus for this PoC, K8s work.
