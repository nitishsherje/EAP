from __future__ import annotations

from .conftest import AGENT_REF


def test_integrity_hash_present_and_valid(app):
    rd = app.resolve(AGENT_REF)
    assert rd.content_hash.startswith("sha256:")
    assert rd.verify_integrity()


def test_tampering_breaks_integrity(app):
    rd = app.resolve(AGENT_REF)
    tampered = rd.model_copy(update={"environment": "prod"})
    # Hash no longer matches the mutated content.
    assert not tampered.verify_integrity()


def test_resolution_map_pins_references(app):
    rd = app.resolve(AGENT_REF)
    assert rd.pin("model://reasoning-standard/1.0.0") == "model://reasoning-standard/1.0.0"
    assert rd.binding_for("capability://document-intelligence/1.0.0") is not None
