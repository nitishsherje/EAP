# §31 — Appendix: Glossary

| Term | Meaning in this repo |
| --- | --- |
| Agent | Reasoning entity (`Agent` resource); uses model + skills/knowledge |
| Skill | Versioned procedure that invokes capabilities; ≠ tool ≠ agent |
| Capability | Logical ability with protocol + operations |
| ToolCall | Runtime record of a capability operation invocation |
| Workflow | Coordinator of agent/skill steps |
| CapabilityBinding | Env-specific adapter/endpoint/auth wiring |
| ResolvedDefinition | Hashed, pinned, bound execution artifact |
| Model Provider | LLM invocation subsystem (not a capability tool) |
| Capability Manager | Routes capability ops to MCP/API/Native clients |
| Knowledge Service | Retrieval intelligence above vector/backends |
| Adapter | Thin transport to an enterprise system |
| InProcessAgentFramework | Current MAF stand-in |
| MAF | Microsoft Agent Framework — **not integrated yet** |
| Control Plane | Validate/register/resolve/govern modules |
| Runtime | Execute ResolvedDefinition |
| Composition root | `EapApplication` / `api_gateway` |
