# ADR 0002 — ResolvedDefinition boundary

## Status

Accepted (implemented)

## Context

Executing mutable YAML risks unreproducible, ungovered runs.

## Decision

Control Plane `Resolver` is the sole producer of `ResolvedDefinition`. Runtime
`ExecutionCoordinator` verifies `content_hash` before strategy execution. Public
`run_agent` / `run_workflow` always resolve first.

## Consequences

- Reproducible pinned bundles per environment  
- Tamper detection via hash  
- Nested bundle not deep-frozen (known partial)  
- Skills cannot be resolved as root targets today  
