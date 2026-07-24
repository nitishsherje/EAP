# §30 — Known Gaps & Technical Debt

## Missing / stubbed functionality

- Microsoft Agent Framework integration  
- `MultiAgentStrategy` / `IterativeStrategy`  
- MCP client transport  
- Postgres metadata/state & S3 artifact implementations  
- Real Milvus search  
- Bearer/OIDC authenticator  
- HTTP route for `run_workflow`  
- First-class Run Skill API  
- True parallel / iterative / dynamic workflow execution  
- Nested workflow steps  
- Workflow `on_error: compensate`  
- Redis cache (optional dep unused)  
- OTel exporter pipeline  
- Online evaluation  

## Architectural drift / temporary implementations

- `InProcessAgentFramework` recreates agent-loop responsibilities  
- CapabilityManager stores guardrail but never applies it  
- HITL `auto_approve=True` in composition root  
- Fake adapters + seeded vector corpus power demos  
- CLI `run-agent <yaml>` does not isolate that file’s registry  
- `run_resolved` / direct strategy|runner|framework calls can skip the full control-plane pipeline (integrity only enforced via coordinator)  
- Runtime DTOs import `Message` from `eap.adapters` (soft layering smell; not an import-linter violation)  
- Adapter factories resolve secrets inside the adapters package (composition logic in a leaf module)  
- Unused leaf stubs: `adapters/database.py`, `adapters/storage.py` ObjectStorage not wired into composition factories  

## Hardcoded / demo configuration

- FakeLLM / FakeDocling response strings  
- InMemoryVector `_SEED_CORPUS`  
- Argo `repoURL` placeholder internal git host  
- Image `REGISTRY/eap` placeholder  

## Security gaps

- AllowAll auth default  
- NoopGuardrail  
- Policy enforce off unless `EAP_AUTH_ENABLED`  
- No secrets-in-logs automated test  

## Testing gaps

- No dedicated secrets non-exposure test  
- No RetryPolicy / circuit-breaker / model-fallback unit tests  
- No adapter test-double injection test (Settings switch exists; not asserted)  
- No dangling in-graph reference test (agent→missing skill/capability during resolve)  
- Weak audit/trace correlation assertions  
- No live gateway integration tests in CI  

## TODOs / NotImplementedError hotspots

Search targets: `persistence/postgres.py`, `persistence/s3.py`, `adapters/milvus.py`, `adapters/storage.py`, `adapters/database.py`, `capabilities/mcp/`, `security` BearerTokenAuthenticator, runtime multi/iterative strategies.
