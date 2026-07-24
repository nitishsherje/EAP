# ADR 0001 — Modular monolith for MVP1

## Status

Accepted (implemented)

## Context

The frozen HLA allows a single API/Runtime deployable and warns against turning
every logical module into a microservice.

## Decision

Ship Control Plane, Runtime, Providers, Capabilities, Knowledge, and Adapters in
**one process** (`EapApplication`), with package boundaries enforced by
import-linter. Optional Worker deferred.

## Consequences

- Simple local demo and K8s Deployment  
- No network hop between resolve and execute  
- Scaling is horizontal replicas of the whole service  
- Long-running/async isolation remains future work  
