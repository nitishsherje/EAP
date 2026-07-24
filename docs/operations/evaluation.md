# §21 — Evaluation

**Package:** `src/eap/evaluation/__init__.py`

| Feature | Status |
| --- | --- |
| Offline regression suite | IMPLEMENTED — `run_suite(runner, cases, evaluators)` |
| Evaluators | IMPLEMENTED — NonEmpty, Contains, Citations |
| Hallucination heuristic | PARTIAL — `detect_hallucination`; used from ResponseService |
| Human feedback capture | IMPLEMENTED — `FeedbackService` + `POST /v1/feedback` |
| Online continuous evaluation | PLANNED / NOT IMPLEMENTED |
| Rich quality metrics / LLM-as-judge | PLANNED / NOT IMPLEMENTED |

Tests: `tests/test_evaluation.py`.

Evaluators operate on any `RunLike` (`content`, `citations`) and do not import runtime — architectural decoupling preserved.
