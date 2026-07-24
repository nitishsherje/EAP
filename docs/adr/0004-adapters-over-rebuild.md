# ADR 0004 — Adapters over rebuilding enterprise capabilities

## Status

Accepted (implemented pattern; many real transports stubbed)

## Context

CRISIL already operates LLM Gateway, Docling, Milvus, S3, databases, APIs, MCP.

## Decision

Portable specs use logical references. Environment `CapabilityBinding` selects
adapter + endpoint + `secret_ref`. Leaf modules under `eap.adapters` perform
transport only. `Settings` toggles fake vs real backends for local development.

## Consequences

- Same Agent YAML across DEV/PROD  
- Walking skeleton works offline with fakes  
- Production readiness requires completing stub adapters and secrets wiring  
