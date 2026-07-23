# Core EAP v1.0 — Enterprise Agent Platform

Specification-driven, governed enterprise agent execution platform built **over**
existing CRISIL AI/data capabilities. EAP does not rebuild infrastructure that
already exists (LLM Gateway, Docling, Milvus, S3, databases, APIs, MCP servers).

## Philosophy

```
Contracts define WHAT
  -> Control Plane validates, versions, resolves and governs
  -> ResolvedDefinition defines exactly WHAT executes
  -> Runtime determines HOW it executes
  -> Microsoft Agent Framework provides agent mechanics
  -> Provider / Capability abstraction invokes enterprise capabilities
  -> Adapters integrate existing CRISIL infrastructure
```

**Architectural invariant:** nothing executes directly from raw mutable
specification. The Runtime only ever executes an immutable, version-pinned,
policy-validated, environment-bound, integrity-hashed `ResolvedDefinition`.

## Module map (`src/eap/`)

| Module | Layer | Responsibility |
| --- | --- | --- |
| `common` | 0 | Errors, ids, events, config (no EAP deps) |
| `specifications` | 0 | Pydantic contracts, references, semver, resolved definition |
| `security` / `observability` / `evaluation` | 1 | Cross-cutting services (injected) |
| `persistence` | 1 | Metadata / artifact / state repositories |
| `adapters` | 3 | Thin transport to CRISIL backends |
| `control_plane` | 2 | Spec service, registry/catalog, resolver, lifecycle, governance |
| `providers` | 4 | Model Provider (LLM invocation) |
| `capabilities` | 4 | Capability Manager (MCP / API / native) |
| `knowledge` | 4 | Knowledge Service (retrieval intelligence) |
| `runtime` | 5 | ExecutionCoordinator, strategies, MAF adapter |
| `api_gateway` | 6 | Composition root, FastAPI surface, CLI |

`contracts/` holds the **declarative** public artifacts (JSON Schema + example
YAML); `src/eap/specifications/` is their **executable** Pydantic form.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows PowerShell
pip install -e ".[dev]"

# Run the end-to-end walking skeleton (no external infra required):
python -m eap.api_gateway.cli demo

# Register + resolve + run an agent from example YAML:
python -m eap.api_gateway.cli run-agent contracts/examples/auditor_report_agent.yaml

# Start the API:
uvicorn eap.api_gateway.app:app --reload
```

The default configuration uses in-process fakes for every backend so the whole
golden path runs on a laptop. Set `EAP_LLM_BACKEND=gateway`,
`EAP_VECTOR_BACKEND=milvus`, etc. to plug real CRISIL capabilities.

## Quality gates

```bash
ruff check .
mypy
lint-imports        # enforces the layered dependency contract
pytest
```
