# §14 — Docling Integration

## Conceptual path (CURRENT)

```text
Skill auditor-extraction
  → capability://document-intelligence (protocol: api)
  → CapabilityManager
  → APIClient
  → build_api_adapter (adapter name "docling" from binding)
  → FakeDoclingAdapter  OR  DoclingGatewayAdapter
  → (gateway) CRISIL Docling HTTP API
```

## Configuration without hardcoding in AgentSpec

| Layer | Contains endpoints/secrets? |
| --- | --- |
| AgentSpec / SkillSpec | **No** — only `capability://…` |
| CapabilitySpec | Paths/operations only (`/v1/parse`) — no host |
| CapabilityBinding (env) | `endpoint`, `adapter: docling`, `auth.secret_ref` |
| Settings | `EAP_DOCLING_BACKEND=fake|gateway` selects concrete class |

Example binding: `contracts/examples/bindings.dev.yaml` → `document-intelligence-dev`.

## Adapters

| Class | File | Status |
| --- | --- | --- |
| `FakeDoclingAdapter` | `adapters/docling.py` | IMPLEMENTED — hardcoded parse response |
| `DoclingGatewayAdapter` | same | PARTIAL — httpx client; needs live gateway |

No Docling business logic is duplicated in EAP — adapters only translate `APIRequest` ↔ HTTP.
