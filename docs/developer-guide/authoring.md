# §25 — Developer Guide (Authoring)

Patterns below match **this repository**. Always register related ModelProfile, Policy, Capability, Knowledge, and **CapabilityBinding** for your target environment before resolve.

## Create an Agent

1. Add YAML under `contracts/examples/` (or your pack) with `kind: Agent`.
2. Reference `model://…`, optional `skill://…`, `knowledge://…`, `policy://…`, `schema://…`.
3. Ensure those targets exist and are published.
4. Provide env binding for the model (and any capabilities/knowledge).
5. Test: `eap resolve agent://your-agent/1.0.0` then `eap run-agent …`.

Mirror structure of `auditor-report-agent.yaml`.

## Create a Skill

1. `kind: Skill`, prefer `type: deterministic` for MVP execution.
2. List `capabilities: [{ ref, operation }]`.
3. Reference from Agent `skills:` or Workflow step `type: skill`.

## Create a Workflow

1. `kind: Workflow` with `steps` and `depends_on`.
2. Remember runtime ignores parallel/dynamic **pattern** flags — use deps for ordering.
3. Run via `EapApplication.run_workflow` (no HTTP route yet) or tests.

## Define a Capability

1. `kind: Capability` with `protocol: api|native|mcp` and `operations`.
2. **Do not** put hosts/secrets in the Capability.
3. Add `CapabilityBinding` per environment (`adapter`, `endpoint`, `secret_ref`).

For API/Docling: set `adapter: docling` or enterprise adapter name recognized by `build_api_adapter`.

## Configure Knowledge

1. `kind: Knowledge` with strategy/top_k/rerank/citations.
2. Binding with `adapter: milvus` (or memory backend via settings) + `config.collection`.
3. Today only vector adapter path is used by KnowledgeService.

## Add an Adapter

1. Implement interface in `adapters/base.py` (`LLMAdapter`, `APIAdapter`, `VectorStoreAdapter`, …).
2. Add factory branch in `adapters/__init__.py` keyed by binding `adapter` name + `Settings.*_backend`.
3. Keep transport-only — no retrieval/governance logic.

## Extend Model Provider

Prefer new behavior inside `ModelProvider` or a new `LLMAdapter`. Do **not** route chat completions through CapabilityManager/MCP.
