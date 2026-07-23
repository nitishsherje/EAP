# §16 — MCP Integration

**Status:** STUBBED interface only.

## Role in architecture

MCP is an **integration protocol** among three (`api`, `mcp`, `native`). It is **not** the EAP architecture and **not** how LLMs are invoked.

## Implementation

File: `src/eap/capabilities/mcp/__init__.py` — class `MCPClient(ToolClient)`.

| Concern | Status |
| --- | --- |
| Client lifecycle | Constructed once in `CapabilityManager.__init__` |
| Tool discovery | `CapabilityManager.discover` reads operations from CapabilitySpec in RD (protocol-agnostic) |
| Tool invocation | `MCPClient.invoke` requires binding then **raises `NotImplementedError`** |
| Authorization | Binding `auth.secret_ref` intended; not exercised |
| Error handling | Manager catches `NotImplementedError` and returns `CapabilityResult(error=…)` |

## CURRENT vs DESIGNED

DESIGNED: wire enterprise MCP SDK (stdio/HTTP) using endpoint/credentials from binding.  
CURRENT: placeholder message instructing implementers to wire the SDK.

There is intentionally **no** separate “MCP Adapter” leaf under `adapters/` — the client speaks MCP directly when implemented.
