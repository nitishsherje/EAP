# Appendix — Specification & configuration examples

Canonical checked-in examples (do not duplicate large YAML here):

| Resource | Path |
| --- | --- |
| Agent | `contracts/examples/auditor-report-agent.yaml` |
| Skill | `contracts/examples/auditor-extraction-skill.yaml` |
| Capability | `contracts/examples/document-intelligence-capability.yaml` |
| Knowledge | `contracts/examples/ratings-knowledge.yaml` |
| Workflow | `contracts/examples/rating-note-workflow.yaml` |
| Bindings (dev) | `contracts/examples/bindings.dev.yaml` |
| Model profiles | `contracts/model_profiles/*.yaml` |
| Policy | `contracts/policies/auditor-guardrails.yaml` |
| Output schema | `contracts/output_schemas/auditor-report.yaml` |
| JSON Schema | `contracts/schemas/*.json` |

## Minimal API examples

```bash
curl -s localhost:8080/health
curl -s localhost:8080/v1/catalog
curl -s -X POST localhost:8080/v1/resolve \
  -H 'content-type: application/json' \
  -d '{"ref":"agent://auditor-report-agent/1.0.0"}'
curl -s -X POST localhost:8080/v1/agents/run \
  -H 'content-type: application/json' \
  -d '{"ref":"agent://auditor-report-agent/1.0.0","query":"flag issues","inputs":{"document_id":"RPT-1"}}'
```

## Env example (laptop)

```bash
set EAP_ENV=dev
set EAP_LLM_BACKEND=fake
set EAP_DOCLING_BACKEND=fake
set EAP_VECTOR_BACKEND=memory
set EAP_METADATA_BACKEND=memory
```
