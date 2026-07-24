# §11 — Skill Architecture

## Distinctions (as implemented)

| Concept | Meaning in EAP |
| --- | --- |
| **Agent** | Reasons with a model; may attach skills/knowledge |
| **Skill** | Versioned procedure that *uses* capabilities; not a transport tool |
| **Capability** | Logical ability with protocol + operations |
| **Tool call (runtime)** | Record of a capability operation invocation (`ToolCall`) |

A skill is **not** an MCP tool and **not** an agent.

## Definition

`Skill` / `SkillSpec` in `specifications/skill.py`.

Example: `contracts/examples/auditor-extraction-skill.yaml`

```yaml
spec:
  type: deterministic
  capabilities:
    - ref: capability://document-intelligence/1.0.0
      operation: parse_document
```

## Resolution

Skills are pulled into `ResolvedDefinition.bundle.skills` when referenced by an agent or workflow during `Resolver` graph walk.

## Execution paths

### 1. Agent-attached (InProcessAgentFramework)

For each skill with `type == deterministic`, invoke each `CapabilityUse` via `invokers.tool`.

Agentic skills are **skipped** in the in-process framework loop.

### 2. Workflow skill step

`WorkflowStrategy._run_skill` — same deterministic capability invocations; agentic types return empty output in MVP1.

## Status

| Skill type | Status |
| --- | --- |
| deterministic | IMPLEMENTED |
| agentic | PARTIALLY — accepted in spec; not executed by in-process framework/workflow helper |
