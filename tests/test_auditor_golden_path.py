"""Focused tests for auditor-report golden path and adapter boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

import httpx
import pytest

from eap.adapters.base import AdapterConfig, APIRequest, LLMRequest, Message
from eap.adapters.docling import DoclingGatewayAdapter, FakeDoclingAdapter, build_fake_auditor_document
from eap.adapters.llm_gateway import CrisilLLMGatewayAdapter, FakeLLMAdapter
from eap.documents import DocumentParseResult, normalize_docling_response
from eap.runtime.skills.auditor_report_analysis import DOCUMENT_CAPABILITY, PARSE_OPERATION

from .conftest import AGENT_REF

ROOT = Path(__file__).resolve().parents[1]


def test_normalize_docling_nested_envelope():
    raw = {
        "result": {
            "document_id": "D1",
            "content": "Opinion text",
            "sections": [{"title": "Opinion", "text": "Present fairly", "page": 1}],
        }
    }
    doc = normalize_docling_response(raw)
    assert isinstance(doc, DocumentParseResult)
    assert doc.document_id == "D1"
    assert doc.sections[0].title == "Opinion"
    assert "Present fairly" in doc.sections[0].text


def test_fake_docling_returns_normalized_auditor_sections():
    adapter = FakeDoclingAdapter()
    resp = adapter.call(APIRequest(method="POST", path="/v1/parse", body={"document_id": "RPT-A"}))
    assert resp.status == 200
    doc = DocumentParseResult.from_dict(resp.body)
    titles = {s.title for s in doc.sections}
    assert "Opinion" in titles
    assert "Basis for Qualified Opinion" in titles
    assert "Key Audit Matters" in titles


def test_fake_llm_structured_auditor_findings():
    adapter = FakeLLMAdapter()
    messages = [
        Message(role="system", content="Analyze auditor report"),
        Message(
            role="user",
            content=(
                "## Basis for Qualified Opinion\nWe were unable to observe physical inventories. "
                "## Emphasis of Matter\nrelated party"
            ),
        ),
    ]
    resp = adapter.complete(LLMRequest(deployment="reasoning-standard", messages=messages, structured=True))
    from eap.providers.llm import ModelProvider

    parsed = ModelProvider._maybe_parse(resp.content)
    assert parsed is not None
    assert parsed["audit_opinion"]["type"] == "qualified"
    assert parsed["qualifications"]
    assert parsed["emphasis_of_matter"]
    assert parsed["evidence"]


def test_llm_gateway_adapter_mocked_http(monkeypatch):
    cfg = AdapterConfig(
        adapter="llm_gateway",
        endpoint="https://llm.example.internal",
        secret="test-key",
        path="/v1/chat/completions",
        correlation_id="corr-1",
    )
    adapter = CrisilLLMGatewayAdapter(cfg)

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": '{"summary":"ok"}'}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                "model": "reasoning-standard",
            }

    class _Client:
        def __init__(self, *a, **k):
            self.headers = k.get("headers") or {}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def request(self, method, path, json=None):
            assert method == "POST"
            assert path == "/v1/chat/completions"
            assert self.headers.get("Authorization") == "Bearer test-key"
            assert self.headers.get("X-Correlation-ID") == "corr-1"
            return _Resp()

    monkeypatch.setattr(httpx, "Client", _Client)
    out = adapter.complete(
        LLMRequest(
            deployment="reasoning-standard",
            messages=[Message(role="user", content="hi")],
            correlation_id="corr-1",
        )
    )
    assert out.content.startswith("{")
    assert out.prompt_tokens == 3


def test_docling_gateway_adapter_normalizes(monkeypatch):
    cfg = AdapterConfig(adapter="docling", endpoint="https://docling.example.internal", secret="dkey")
    adapter = DoclingGatewayAdapter(cfg)

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"document": {"document_id": "X", "content": "raw", "sections": []}}

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def request(self, *a, **k):
            return _Resp()

    monkeypatch.setattr(httpx, "Client", _Client)
    resp = adapter.call(APIRequest(method="POST", path="/v1/parse", body={"document_id": "X"}))
    assert resp.body["document_id"] == "X"
    assert "text" in resp.body


def test_capability_manager_document_parse(app):
    rd = app.resolve(AGENT_REF)
    result = app.capability_manager.invoke(
        rd, DOCUMENT_CAPABILITY, PARSE_OPERATION, {"document_id": "RPT-PARSE"}
    )
    assert result.ok
    assert result.output["document_id"] == "RPT-PARSE"
    assert result.output["sections"]


def test_auditor_skill_module_has_no_adapter_imports():
    path = ROOT / "src" / "eap" / "runtime" / "skills" / "auditor_report_analysis.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = [m for m in imported if "adapters.docling" in m or "adapters.llm" in m or m.endswith("httpx")]
    assert not forbidden, f"skill imports infrastructure: {forbidden}"


def test_auditor_report_e2e_structured(app):
    result = app.run_agent(
        AGENT_REF,
        query="Analyze the Independent Auditor's Report",
        inputs={"document_id": "RPT-GOLDEN"},
    )
    assert result.status == "succeeded"
    assert result.output.get("structured")
    structured = result.output["structured"]
    assert "summary" in structured
    assert "audit_opinion" in structured
    assert structured["audit_opinion"]["type"] in {"qualified", "unqualified", "unknown"}
    assert "evidence" in structured
    ops = {(tc.capability, tc.operation) for tc in result.tool_calls}
    assert (DOCUMENT_CAPABILITY, PARSE_OPERATION) in ops
    assert result.output.get("schema_valid") is True


def test_build_fake_auditor_document_excludes_kam_as_qualification_source():
    doc = build_fake_auditor_document("R1")
    kam = [s for s in doc.sections if "Key Audit" in s.title]
    assert kam  # present in document
    # Selection helper used by skill excludes KAMs from analysis inputs.
    from eap.runtime.skills.auditor_report_analysis import _select_auditor_sections

    selected_titles = {s["title"] for s in _select_auditor_sections(doc)}
    assert not any("Key Audit" in t for t in selected_titles)
