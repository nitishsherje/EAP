# §27 — Testing Strategy

**Location:** `tests/`

| Kind | What exists | Evidence |
| --- | --- | --- |
| Unit / contract (specs) | References, SemVer, invalid fields | `test_specifications.py` |
| Control plane | Resolve bundle, policy, unpublished, missing binding | `test_control_plane.py` |
| RD integrity | Hash + tamper | `test_resolved_definition.py` |
| Runtime e2e | Agent run, tokens, refuse tampered | `test_runtime.py` |
| Workflow e2e | Skill+agent steps | `test_workflow.py` |
| API integration | FastAPI TestClient | `test_api.py` |
| Evaluation | Suite + hallucination + feedback | `test_evaluation.py` |
| Architecture | import-linter in CI | `pyproject.toml` + workflow |

## Invariant → test map

| Architectural invariant | Test coverage |
| --- | --- |
| Invalid AgentSpec rejected | PASS — scheme validation test |
| Version selection deterministic | PASS — SemVer tests |
| Env binding required | PASS — `test_missing_binding_raises` |
| Tampered RD cannot run | PASS — `test_refuses_tampered_resolved_definition` |
| Agent uses resolved capabilities | PASS — tool_calls assertion |
| Secrets not logged/in specs | **FAIL / missing dedicated test** |
| Retry behavior | **FAIL / missing** |
| Adapter swap test double | PARTIAL — settings switch, no explicit unit |
| Audit correlation asserted | PARTIAL — events exist, weak asserts |

Fixtures: `tests/conftest.py` builds `EapApplication` with example contracts.
