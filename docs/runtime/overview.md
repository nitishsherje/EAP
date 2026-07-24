# §7 — Runtime Architecture

**Package:** `src/eap/runtime/`  
**Status:** PARTIALLY IMPLEMENTED (single-agent + workflow graph work; MAF/multi/iterative do not)

## Entry point

`ExecutionCoordinator.run(rd: ResolvedDefinition, request: ExecutionRequest) -> ExecutionResult`

File: `runtime/execution/__init__.py`

1. `rd.verify_integrity()` — refuse if false  
2. Persist `RunRecord` (RUNNING)  
3. Publish `RUN_STARTED`  
4. Select strategy by `rd.root_kind`  
5. `context_service.build` → `strategy.execute`  
6. Persist result / checkpoint / events  

## Strategies

| Strategy | File | Status |
| --- | --- | --- |
| `SingleAgentStrategy` | `strategies/single_agent.py` | IMPLEMENTED |
| `WorkflowStrategy` | `strategies/workflow.py` | IMPLEMENTED (topo-order) |
| `MultiAgentStrategy` | `strategies/multi_agent.py` | STUBBED |
| `IterativeStrategy` | `strategies/iterative.py` | STUBBED |

## Shared agent helper

`runtime/agent_runner.py`:

- `build_invokers(rd, agent, services, request)` → model / tool / knowledge callables  
- `run_agent(...)` → `framework.run_agent` → `ResponseService.build`

## Supporting services

| Service | Module | Status | Behavior |
| --- | --- | --- | --- |
| ContextService | `context/` | IMPLEMENTED | Builds `ExecutionContext` + instructions from agent/prompt |
| MemoryService | `memory/` | IMPLEMENTED | In-process session history |
| StateCheckpointService | `state/` | IMPLEMENTED | Wraps `StateStore` (memory default) |
| HITLService | `hitl/` | PARTIAL | Requests approval; assembly sets `auto_approve=True` |
| ResponseService | `response/` | PARTIAL | Schema check + NoopGuardrail + hallucination heuristic |

## Call chain — agent

```text
ExecutionCoordinator.run
  → SingleAgentStrategy.execute
       → (optional HITL if classification == restricted)
       → run_agent
            → InProcessAgentFramework.run_agent
                 → knowledge invoker(s)
                 → skill capability invokers
                 → model invoker
            → ResponseService.build
```

## Call chain — workflow

```text
ExecutionCoordinator.run
  → WorkflowStrategy.execute
       → topo_order(depends_on)
       → for each step:
            skill → CapabilityManager.invoke
            agent → run_agent(...)
            workflow → ExecutionError (unsupported)
```

## Skill execution

No standalone Run Skill API. Skills execute:

1. Inside `InProcessAgentFramework` for agent-attached deterministic skills  
2. Inside `WorkflowStrategy._run_skill` for workflow skill steps  

## Dependency injection

`RuntimeServices` (`deps.py`) holds settings, secrets, model_provider, capability_manager, knowledge_service, context/memory/state/hitl/response, framework, events, telemetry, metadata_repo.
