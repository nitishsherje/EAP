# §9 — Agent Architecture

## How an AgentSpec becomes executable

```mermaid
sequenceDiagram
  participant YAML as Agent YAML
  participant CP as ControlPlane
  participant RD as ResolvedDefinition
  participant EC as ExecutionCoordinator
  participant SA as SingleAgentStrategy
  participant FW as InProcessAgentFramework
  participant MP as ModelProvider
  participant CM as CapabilityManager
  participant KS as KnowledgeService

  YAML->>CP: register + publish
  CP->>RD: resolve(agent://..., env)
  Note over RD: pins models, skills, caps, knowledge, bindings, policy, hash
  RD->>EC: run(rd, request)
  EC->>SA: execute
  SA->>FW: run_agent(invocation, invokers)
  FW->>KS: retrieve
  FW->>CM: invoke (via skill)
  FW->>MP: invoke
  FW-->>SA: FrameworkResult
  SA-->>EC: ExecutionResult
```

## Trace (files)

| Step | Location |
| --- | --- |
| Spec | `contracts/examples/auditor-report-agent.yaml` → `Agent` / `AgentSpec` |
| Resolve | `Resolver.resolve` |
| Run API | `EapApplication.run_agent` → `_run_target` |
| Coordinate | `ExecutionCoordinator.run` |
| Strategy | `SingleAgentStrategy.execute` |
| Framework | `InProcessAgentFramework.run_agent` (**not MAF**) |
| Model | `ModelProvider.invoke(rd, agent.spec.model, …)` |
| Skills/caps | `CapabilityManager.invoke` |
| Knowledge | `KnowledgeService.retrieve` |
| Response | `ResponseService.build` |

## Notes

- Direct `agent.spec.capabilities` are passed on `AgentInvocation` but **unused** by `InProcessAgentFramework` (skills drive tool calls).  
- HITL triggers only when `effective_policy.data_classification == "restricted"` and approval is not auto-approved.
