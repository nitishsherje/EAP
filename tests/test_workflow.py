from __future__ import annotations

WORKFLOW_REF = "workflow://rating-note-generation/1.0.0"


def test_run_workflow_end_to_end(app):
    result = app.run_workflow(
        WORKFLOW_REF, query="Generate the rating note", inputs={"document_id": "RPT-7"}
    )
    assert result.status == "succeeded"
    # The skill step invoked the document-intelligence capability.
    ops = {(tc.capability, tc.operation) for tc in result.tool_calls}
    assert ("capability://document-intelligence/1.0.0", "parse_document") in ops
    # The agent step produced content and tokens.
    assert result.content
    assert result.total_tokens > 0
    assert "extract" in result.output["steps"]
    assert "analyze" in result.output["steps"]


def test_workflow_resolves_as_root(app):
    rd = app.resolve(WORKFLOW_REF)
    assert rd.root_kind.value == "Workflow"
    assert rd.root_workflow is not None
