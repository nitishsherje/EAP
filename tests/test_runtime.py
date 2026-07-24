from __future__ import annotations

import pytest

from eap.common.errors import ExecutionError
from eap.runtime import ExecutionRequest
from eap.security import Principal

from .conftest import AGENT_REF


def test_run_agent_end_to_end(app):
    result = app.run_agent(
        AGENT_REF, query="Analyze the report", inputs={"document_id": "RPT-1"}
    )
    assert result.status == "succeeded"
    assert result.content
    assert result.total_tokens > 0
    # Skill invoked its capability (skill != tool).
    ops = {(tc.capability, tc.operation) for tc in result.tool_calls}
    assert ("capability://document-intelligence/1.0.0", "parse_document") in ops
    # Knowledge citations assembled.
    assert result.citations


def test_run_records_persisted(app):
    result = app.run_agent(AGENT_REF, query="hi", inputs={"document_id": "RPT-2"})
    run = app.metadata_repo.get_run(result.run_id)
    assert run is not None
    assert run.status.value == "succeeded"
    assert run.resolved_hash.startswith("sha256:")


def test_finops_tokens_tracked(app):
    app.run_agent(AGENT_REF, query="hi", inputs={"document_id": "RPT-3"})
    assert app.token_tracker.total_tokens() > 0


def test_refuses_tampered_resolved_definition(app):
    rd = app.resolve(AGENT_REF)
    tampered = rd.model_copy(update={"environment": "prod"})
    # The immutable-execution invariant refuses to run a non-verifying artifact.
    with pytest.raises(ExecutionError, match="integrity"):
        app.run_resolved(tampered, ExecutionRequest(principal=Principal.system()))
