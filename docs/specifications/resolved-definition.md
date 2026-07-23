# §6 — ResolvedDefinition

**Status:** IMPLEMENTED as the Control Plane → Runtime contract, with shallow immutability.

## Why it exists

Architectural invariant (documented in `resolved_definition.py` and README):

> The Runtime executes a ResolvedDefinition, never raw mutable YAML.

It is immutable (top-level), version-pinned, environment-bound, policy-captured, and integrity-hashed.

## How it is created

1. `Resolver.resolve(ref, environment, principal)` in `control_plane/resolver/__init__.py`
2. Walks agent/workflow dependency graph into `ResolvedBundle`
3. Maps every ref via `resolution_map` to pinned `scheme://name/x.y.z`
4. Inlines bindings for the target environment (`bindings` dict)
5. Builds `EffectivePolicy` via `GovernanceService`
6. `definition.finalize()` sets `content_hash = sha256:…`

## Fields (summary)

| Field | Role |
| --- | --- |
| `target` | Pinned root ref |
| `root_kind` | Agent or Workflow |
| `environment` | Binding environment |
| `bundle` | Agents, skills, capabilities, knowledge, models, policies, bindings, resolution_map |
| `effective_policy` | Flattened classification, guardrails, scopes |
| `provenance` | Who/when/source_ref |
| `content_hash` | Integrity |

Helpers: `pin(ref)`, `binding_for(ref)`, `verify_integrity()`, `root_agent` / `root_workflow`.

## Immutability — PARTIALLY IMPLEMENTED

```python
# ResolvedDefinition
model_config = ConfigDict(frozen=True)

# ResolvedBundle
model_config = ConfigDict(extra="forbid")  # NOT frozen
```

Top-level attribute assignment is blocked. Nested mutation of `bundle` collections is still possible in Python. Runtime mitigates via `verify_integrity()` before execute.

## Version pinning — IMPLEMENTED

`resolution_map` and bundle keys use pinned refs. Runtime uses `rd.pin(...)` and never re-queries the registry.

## Environment binding — IMPLEMENTED

Bindings filtered by environment during resolve. Wrong env → `ResolutionError` (BINDING_MISSING).

## Policy validation — PARTIALLY IMPLEMENTED

Effective policy always captured. `GovernanceService.authorize` / enforce depends on `enforce_policies` (wired from `Settings.auth_enabled`, default **False**).

## Integrity / reproducibility — IMPLEMENTED

`compute_hash` over canonical JSON excluding volatile fields. `ExecutionCoordinator.run` refuses non-verifying RDs (`ExecutionError`). Test: `test_refuses_tampered_resolved_definition`.

## Can raw specs execute directly?

**On the public application path: No.**

```text
EapApplication.run_agent / run_workflow
  → _run_target
  → resolve(...)           # always
  → coordinator.run(rd)    # integrity check
```

There is **no** first-class “load YAML and execute” product path. CLI `run-agent <file.yaml>` only extracts the agent **ref**, then resolves against the **preloaded** example registry (`build_app_with_examples`) — disk YAML is not the execution source of truth.

### Bypass surface (in-process) — PARTIAL seal

The integrity gate is real at `ExecutionCoordinator.run`, but the boundary is **not sealed** against lower-layer callers:

| Path | Skips control-plane resolve/bind/govern? | Integrity check? |
| --- | --- | --- |
| `run_agent` / `run_workflow` / HTTP `/v1/agents/run` | No | Yes |
| `EapApplication.run_resolved(rd, request)` | Yes (caller supplies RD) | Yes (coordinator) |
| Hand-built `ResolvedDefinition.finalize()` + `coordinator.run` | Yes | Yes (hash must match content) |
| Direct `SingleAgentStrategy.execute` / `WorkflowStrategy.execute` | Yes | **No** |
| Direct `agent_runner.run_agent` / `InProcessAgentFramework.run_agent` | Yes | **No** |

**Implication:** API/CLI happy path holds the invariant. Library consumers that import strategies or the framework can execute without going through validate→register→resolve→bind→govern. Treat that as known debt until those entry points are restricted or also gated.
