# §26 — Local Development Guide

## Prerequisites

- Python **3.11+**
- Git
- Optional: Docker (image build), kubectl/kustomize (manifest render only)

## Installation

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\activate
pip install -e ".[dev]"
# Optional real clients:
# pip install -e ".[adapters]"
```

## Configuration

Defaults need no external infra (all fakes/memory). Override with env vars from [operations/configuration.md](../operations/configuration.md).

## Startup

```bash
# Walking skeleton demo
python -m eap.api_gateway.cli demo
# or
eap demo

# API
uvicorn eap.api_gateway.app:app --reload --port 8080
```

Health: `GET http://127.0.0.1:8080/health`

## Tests & quality

```bash
ruff check .
mypy
lint-imports
pytest -q
python scripts/generate_schemas.py   # then ensure contracts/schemas clean
```

## Sample execution

```bash
eap catalog
eap resolve agent://auditor-report-agent/1.0.0
eap run-agent agent://auditor-report-agent/1.0.0 --document-id RPT-1
```

Note: `eap run-agent path/to.yaml` extracts the agent ref from the file but still runs against the **preloaded** example registry from `build_app_with_examples()`, not a fresh isolated registry containing only that file.
