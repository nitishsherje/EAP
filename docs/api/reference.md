# §24 — API Reference

**App:** `src/eap/api_gateway/app.py`  
**Composition:** module loads `build_app_with_examples()` at import (registers all `contracts/` YAML).

Authentication: optional `Authorization: Bearer <token>` → `AllowAllAuthenticator` (default).

Errors: `EapError` mapped to HTTP 401/403/404/409/400 via `_handle`.

---

### `GET /health` — IMPLEMENTED

Response: `{ "status": "ok", "version": "1.0.0" }`

---

### `GET /v1/catalog` — IMPLEMENTED

Lists catalog entries (`kind`, `name`, `version`, `status`, `domain`, …).

---

### `POST /v1/specs` — IMPLEMENTED

Request:

```json
{ "resource": { "apiVersion": "eap.crisil/v1", "kind": "Agent", "metadata": {…}, "spec": {…} }, "publish": false }
```

Response: `{ "registered": "<key>", "published": bool }`

---

### `POST /v1/resolve` — IMPLEMENTED

Request: `{ "ref": "agent://auditor-report-agent/1.0.0", "environment": "dev" }`  
Response: `target`, `environment`, `content_hash`, `effective_policy`, `bindings` (keys).

---

### `POST /v1/agents/run` — IMPLEMENTED

Request:

```json
{
  "ref": "agent://auditor-report-agent/1.0.0",
  "query": "flag issues",
  "inputs": { "document_id": "RPT-9" },
  "environment": null
}
```

Response: `run_id`, `status`, `content`, `output`, `citations`, `tokens`, `used_fallback`, `error`.

---

### `POST /v1/feedback` — IMPLEMENTED

Request: `{ "run_id": "…", "rating": 5, "comment": "" }`  
Response: `{ "id", "run_id", "rating" }`

---

### `GET /v1/runs/{run_id}` — IMPLEMENTED

Returns `RunRecord.model_dump()` or 404.

---

### Not exposed over HTTP (but exist on `EapApplication`)

| Method | Status |
| --- | --- |
| `run_workflow` | IMPLEMENTED in assembly; **no route** |
| Direct `run_resolved` | Library only |

## CLI (`eap`)

| Command | Behavior |
| --- | --- |
| `eap demo` | Load examples; run auditor agent |
| `eap catalog` | Print catalog table |
| `eap resolve <ref>` | Print RD summary |
| `eap run-agent <ref\|yaml> [--query] [--document-id]` | Resolve+run |

Entry point: `pyproject.toml` → `eap = eap.api_gateway.cli:main`.
