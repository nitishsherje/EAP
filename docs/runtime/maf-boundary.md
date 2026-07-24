# §8 — Microsoft Agent Framework Integration

## DESIGNED ARCHITECTURE

| EAP owns | MAF owns |
| --- | --- |
| Specs, registry, resolution, governance, lifecycle | Agent execution loop |
| Capability / knowledge abstraction | Workflow / multi-agent primitives |
| Enterprise adapters, observability, evaluation | Tool-calling mechanics |

EAP should inject Model Provider and Capability/Knowledge invokers as MAF model/tool clients without leaking MAF types into domain models.

## CURRENT IMPLEMENTATION

**Microsoft Agent Framework is not a dependency and is not invoked.**

Isolation seam exists:

| Type | File | Role |
| --- | --- | --- |
| `AgentFrameworkAdapter` (ABC) | `runtime/framework.py` | `run_agent(invocation, invokers)` |
| `InProcessAgentFramework` | same | Deterministic stand-in |
| `AgentInvocation`, `Invokers`, `FrameworkResult` | same | EAP-native DTOs |

Wired in `EapApplication.__init__`:

```python
framework=InProcessAgentFramework()
```

### What `InProcessAgentFramework` actually does

1. Retrieve knowledge for each `knowledge_refs` entry  
2. For each **deterministic** skill, invoke each capability operation via `invokers.tool`  
3. Assemble system/user messages and call `invokers.model` once  
4. Return content, citations, tool_calls, tokens  

It does **not** implement a multi-turn tool-calling agent loop, MAF workflows, or multi-agent orchestration.

### Gap statement

Until a MAF-backed adapter is implemented, documentation and architecture reviews must treat agent mechanics as **EAP-owned temporary code**, not MAF.

Recommended path (not implemented): `MafAgentFramework(AgentFrameworkAdapter)` mapping `AgentInvocation` → MAF agent + tools.
