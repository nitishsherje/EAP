# Core EAP v1.0 — Sequence Diagrams (Phase 4)

> **Note:** Prefer diagrams in the v1.0 doc set ([`../README.md`](../README.md))
> when distinguishing MAF (designed) vs `InProcessAgentFramework` (current).

Runtime interactions for the primary flows. Participants map to components under
`src/eap/` — verify stand-ins/stubs before operational use.

## 1. Register a specification

```mermaid
sequenceDiagram
    actor Author
    participant API as API Gateway
    participant CP as ControlPlane
    participant SS as SpecificationService
    participant REG as Registry
    participant REPO as MetadataRepository
    participant BUS as EventBus

    Author->>API: POST /v1/specs {resource}
    API->>API: parse_resource (schema validation)
    API->>CP: register(resource, principal)
    CP->>SS: ingest(resource)
    SS->>SS: validate (semantic + compatibility)
    SS->>REG: register(DRAFT)
    REG->>REPO: put_resource (immutable per version)
    CP->>BUS: publish(spec.registered)
    API-->>Author: {registered: kind:name:version}
```

## 2. Resolve an agent (produce ResolvedDefinition)

```mermaid
sequenceDiagram
    participant API as API Gateway
    participant CP as ControlPlane
    participant R as Resolver
    participant REG as Registry
    participant GOV as GovernanceService
    participant ART as ArtifactStore

    API->>CP: resolve(agent://.., env, principal)
    CP->>R: resolve(ref, env)
    loop dependency graph
        R->>REG: resolve(ref) -> pinned published version
        R->>R: pin, add to bundle, recurse
        R->>REG: find CapabilityBinding(target, env)
    end
    R->>GOV: build_effective_policy(policies, classifications, scopes)
    R->>GOV: authorize(principal, "resolve", target)
    R->>R: finalize() -> content_hash (SHA-256)
    CP-->>API: ResolvedDefinition
    API->>ART: put(resolved/<hash>.json)
```

## 3. Run an agent

```mermaid
sequenceDiagram
    participant API as API Gateway
    participant EC as ExecutionCoordinator
    participant CTX as ContextService
    participant ST as SingleAgentStrategy
    participant MAF as AgentFrameworkAdapter
    participant MP as ModelProvider
    participant CM as CapabilityManager
    participant KS as KnowledgeService
    participant RS as ResponseService

    API->>EC: run(rd, request)
    EC->>EC: verify_integrity(rd)  %% refuse if tampered
    EC->>CTX: build(rd, request)
    EC->>ST: execute(ctx, services)
    ST->>MAF: run_agent(invocation, invokers)
    MAF->>KS: retrieve(knowledge_ref, query)
    MAF->>CM: invoke(capability_ref, op, inputs)  %% via deterministic skill
    MAF->>MP: model(messages, structured)
    MAF-->>ST: FrameworkResult
    ST->>RS: build(content, structured, citations)
    ST-->>EC: ExecutionResult
    EC->>EC: checkpoint + RUN_COMPLETED
    EC-->>API: ExecutionResult
```

## 4. Run a workflow

```mermaid
sequenceDiagram
    participant EC as ExecutionCoordinator
    participant WF as WorkflowStrategy
    participant CM as CapabilityManager
    participant AR as agent_runner
    participant MAF as AgentFrameworkAdapter

    EC->>WF: execute(ctx, services)
    WF->>WF: topological order (depends_on)
    loop each step
        alt skill step
            WF->>CM: invoke(cap_ref, op, resolved_inputs)
        else agent step
            WF->>AR: run_agent(rd, agent, inputs)
            AR->>MAF: run_agent(invocation, invokers)
        end
        WF->>WF: store step output, resolve ${placeholders}
    end
    WF-->>EC: ExecutionResult(steps, targets)
```

## 5. LLM invocation (with fallback)

```mermaid
sequenceDiagram
    participant MP as ModelProvider
    participant CB as CircuitBreaker
    participant AD as LLMAdapter
    participant GW as CRISIL LLM Gateway
    participant TT as TokenTracker

    MP->>MP: routing_chain = [primary, ...fallback]
    loop chain
        MP->>CB: call(retry(adapter.complete))
        CB->>AD: complete(request)
        AD->>GW: POST /v1/chat/completions
        alt success
            GW-->>AD: completion + usage
            MP->>TT: record(TokenUsage)
        else failure
            MP->>MP: try next in chain
        end
    end
    MP-->>MP: ModelResult
```

## 6. Capability via Docling (API protocol)

```mermaid
sequenceDiagram
    participant CM as CapabilityManager
    participant AC as APIClient
    participant DA as DoclingAdapter
    participant DG as Docling Gateway

    CM->>CM: pin ref, find operation + binding
    CM->>AC: invoke(capability, operation, inputs, binding)
    AC->>DA: call(APIRequest POST /v1/parse)
    DA->>DG: HTTP request (auth from secret_ref)
    DG-->>DA: parsed document
    DA-->>AC: APIResponse
    AC-->>CM: normalized body
```

## 7. Capability via MCP

```mermaid
sequenceDiagram
    participant CM as CapabilityManager
    participant MC as MCPClient
    participant MS as Enterprise MCP Server

    CM->>MC: invoke(capability, operation, inputs, binding)
    MC->>MS: MCP call (endpoint/creds from binding)
    MS-->>MC: tool result
    MC-->>CM: normalized body
    note over MC: MVP1 ships the interface + minimal client
```

## 8. Knowledge retrieval

```mermaid
sequenceDiagram
    participant KS as KnowledgeService
    participant VA as VectorStoreAdapter
    participant MV as Milvus

    KS->>KS: resolve KnowledgeSpec + binding, plan query
    KS->>VA: search(collection, VectorQuery)
    VA->>MV: vector/hybrid search
    MV-->>VA: hits
    KS->>KS: permission filter (classification vs principal)
    KS->>KS: rerank (pluggable) + assemble citations
    KS-->>KS: RetrievalResult(chunks, citations)
```

## 9. Human-in-the-loop (approval + resume)

```mermaid
sequenceDiagram
    participant ST as Strategy
    participant HITL as HITLService
    participant BUS as EventBus
    actor Approver

    ST->>HITL: request(run_id, reason)  %% e.g. restricted data
    HITL->>BUS: publish(hitl.requested)
    alt auto-approve (dev)
        HITL-->>ST: APPROVED
    else manual
        Approver->>HITL: resolve(request_id, approved)
        HITL->>BUS: publish(hitl.resolved)
    end
    ST->>ST: continue or return waiting_hitl
```

## 10. Failure, retry & resume

```mermaid
sequenceDiagram
    participant EC as ExecutionCoordinator
    participant ST as Strategy
    participant SS as StateCheckpointService
    participant BUS as EventBus

    EC->>ST: execute(ctx)
    alt error
        ST-->>EC: raises EapError
        EC->>BUS: publish(run.failed)
        EC-->>EC: RunRecord FAILED
    else success
        ST-->>EC: ExecutionResult
        EC->>SS: checkpoint(run_id, "completed", output)
        EC->>BUS: publish(run.completed)
    end
    note over EC,SS: A later run may resume_from a checkpoint
```

## 11. Evaluation & feedback

```mermaid
sequenceDiagram
    participant Suite as run_suite
    participant Runner
    participant Ev as Evaluators
    participant HH as detect_hallucination
    actor User
    participant FS as FeedbackService
    participant BUS as EventBus

    Suite->>Runner: run(case) -> RunLike
    Suite->>Ev: evaluate(case, run)
    Ev-->>Suite: EvalResult (contains/citations/non-empty)
    Note over HH: ResponseService calls detect_hallucination per run
    User->>FS: record(run_id, rating, comment)
    FS->>BUS: publish(feedback.recorded)
```
