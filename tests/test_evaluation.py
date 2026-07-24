from __future__ import annotations

from eap.evaluation import (
    EvalCase,
    detect_hallucination,
    run_suite,
)

from .conftest import AGENT_REF


def test_regression_suite_passes(app):
    cases = [
        EvalCase(
            id="auditor-basic",
            ref=AGENT_REF,
            query="Analyze the auditor report",
            inputs={"document_id": "RPT-100"},
            expected_contains=["analysis"],
            expect_citations=True,
        )
    ]

    def runner(case: EvalCase):
        return app.run_agent(case.ref, query=case.query, inputs=case.inputs)

    report = run_suite(runner, cases)
    assert report.passed, report.failures()
    assert report.pass_rate == 1.0


def test_hallucination_hook_flags_ungrounded():
    signal = detect_hallucination("A long substantive claim " * 5, citations=[])
    assert signal.flagged

    grounded = detect_hallucination("A long substantive claim " * 5, citations=["src.pdf"])
    assert not grounded.flagged


def test_feedback_capture_emits_event(app):
    received = []
    app.events.subscribe("feedback.recorded", lambda e: received.append(e))
    result = app.run_agent(AGENT_REF, query="hi", inputs={"document_id": "RPT-5"})
    fb = app.record_feedback(result.run_id, rating=1, comment="useful")
    assert fb.run_id == result.run_id
    assert app.feedback.for_run(result.run_id)
    assert received and received[0].payload["rating"] == 1
