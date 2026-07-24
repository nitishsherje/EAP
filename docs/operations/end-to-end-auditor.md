# Auditor Report Golden Path (implemented)

Local fake mode (no Docker/AWS/credentials):

```bash
pip install -e ".[dev]"
eap demo
# or
eap run-agent agent://auditor-report-agent/1.0.0 --document-id RPT-2026-042
```

Flow (actual):

```
AgentSpec (auditor-report-agent)
  → ControlPlane.resolve → ResolvedDefinition
  → ExecutionCoordinator → InProcessAgentFramework
  → FUNCTION skill auditor-report-analysis
       → CapabilityManager.parse_document → FakeDoclingAdapter (normalized DocumentParseResult)
       → ModelProvider → FakeLLMAdapter (structured findings JSON)
  → Governed Response (schema://auditor-report)
```

Enterprise mode: set `EAP_LLM_BACKEND=gateway`, `EAP_DOCLING_BACKEND=gateway`, plus
`LLM_GATEWAY_BASE_URL` / `DOCLING_BASE_URL` and API keys (see README / operations config).
Do not put URLs or secrets in Agent/Skill YAML.
