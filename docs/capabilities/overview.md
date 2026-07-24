# §12 — Capability Architecture

## Components

| Piece | Location | Status |
| --- | --- | --- |
| CapabilitySpec | `specifications/capability.py` | IMPLEMENTED |
| CapabilityManager | `capabilities/manager/__init__.py` | PARTIAL (routing works; guardrail unused) |
| APIClient | `capabilities/api/` | IMPLEMENTED |
| NativeRunner | `capabilities/native/` | IMPLEMENTED |
| MCPClient | `capabilities/mcp/` | STUBBED |

## Routing

```text
CapabilityManager.invoke(rd, capability_ref, operation, inputs)
  → pin ref, load Capability from RD
  → select client by capability.spec.protocol
  → client.invoke(capability, operation, inputs, binding)
```

Clients map:

| Protocol | Client |
| --- | --- |
| `api` | `APIClient` → `build_api_adapter` (docling / enterprise) |
| `native` | `NativeRunner` + `NativeToolRegistry` |
| `mcp` | `MCPClient` → raises `NotImplementedError` |

## End-to-end: document-intelligence (IMPLEMENTED with fake default)

```mermaid
sequenceDiagram
  participant Skill as auditor-extraction skill
  participant CM as CapabilityManager
  participant API as APIClient
  participant Ad as FakeDoclingAdapter / DoclingGatewayAdapter
  participant GW as Docling Gateway

  Skill->>CM: invoke(capability://document-intelligence, parse_document, inputs)
  CM->>API: protocol=api
  API->>Ad: APIRequest POST /v1/parse
  alt EAP_DOCLING_BACKEND=fake
    Ad-->>API: fake parsed body
  else gateway
    Ad->>GW: HTTP
    GW-->>Ad: JSON
  end
```

Evidence: `tests/test_runtime.py` asserts tool call `(capability://document-intelligence/1.0.0, parse_document)`.

## Gaps

- Per-invocation guardrails documented in module docstring but `_guardrail` never called in `invoke`.  
- No duplicated MCP→Adapter→MCP layer (good) — MCP simply unimplemented.
