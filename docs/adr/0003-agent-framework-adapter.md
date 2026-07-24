# ADR 0003 — Agent framework adapter seam

## Status

Accepted seam; MAF integration **not** implemented

## Context

HLA assigns agent-loop mechanics to Microsoft Agent Framework while EAP owns
governance and enterprise integration.

## Decision

Introduce `AgentFrameworkAdapter` with EAP-native DTOs (`AgentInvocation`,
`Invokers`). Ship `InProcessAgentFramework` as a deterministic stand-in so the
golden path runs without MAF.

## Consequences

- Domain code does not import MAF types (good)  
- Current stand-in **recreates** some MAF responsibilities (debt)  
- Multi-agent / iterative strategies remain stubs pending MAF primitives  
