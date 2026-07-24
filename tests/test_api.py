from __future__ import annotations

from fastapi.testclient import TestClient

from eap.api_gateway.app import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_catalog_lists_examples():
    resp = client.get("/v1/catalog")
    assert resp.status_code == 200
    names = {e["name"] for e in resp.json()}
    assert "auditor-report-agent" in names


def test_resolve_endpoint():
    resp = client.post(
        "/v1/resolve", json={"ref": "agent://auditor-report-agent/1.0.0"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content_hash"].startswith("sha256:")
    assert body["effective_policy"]["data_classification"] == "confidential"


def test_run_agent_endpoint():
    resp = client.post(
        "/v1/agents/run",
        json={
            "ref": "agent://auditor-report-agent/1.0.0",
            "query": "flag issues",
            "inputs": {"document_id": "RPT-9"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["content"]
    run_id = body["run_id"]

    run_resp = client.get(f"/v1/runs/{run_id}")
    assert run_resp.status_code == 200
    assert run_resp.json()["status"] == "succeeded"


def test_resolve_unknown_ref_404():
    resp = client.post("/v1/resolve", json={"ref": "agent://does-not-exist/1.0.0"})
    assert resp.status_code == 404
