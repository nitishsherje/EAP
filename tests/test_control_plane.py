from __future__ import annotations

import pytest

from eap.common.config import Settings
from eap.common.errors import NotFoundError, ResolutionError
from eap.common.events import InProcessEventBus
from eap.control_plane import ControlPlane
from eap.persistence import build_metadata_repository
from eap.security import LoggingAuditLogger, Principal
from eap.specifications.loader import load_yaml

from .conftest import AGENT_REF


def _cp():
    settings = Settings.load()
    return ControlPlane(
        build_metadata_repository(settings), InProcessEventBus(), LoggingAuditLogger()
    )


def test_resolve_builds_full_bundle(app):
    rd = app.resolve(AGENT_REF)
    assert rd.target == AGENT_REF
    assert rd.verify_integrity()
    assert set(rd.bundle.agents) == {AGENT_REF}
    assert "skill://auditor-extraction/2.1.0" in rd.bundle.skills
    assert "capability://document-intelligence/1.0.0" in rd.bundle.capabilities
    assert "knowledge://ratings-knowledge/2.0.0" in rd.bundle.knowledge
    # model + fallback both pinned and bound
    assert "model://reasoning-standard/1.0.0" in rd.bundle.models
    assert "model://reasoning-fallback/1.0.0" in rd.bundle.models
    assert len(rd.bundle.bindings) == 4


def test_effective_policy_captures_classification(app):
    rd = app.resolve(AGENT_REF)
    assert rd.effective_policy.data_classification == "confidential"
    assert "document.read" in rd.effective_policy.required_scopes


def test_unpublished_cannot_resolve():
    cp = _cp()
    agent = load_yaml(
        """
apiVersion: eap.crisil/v1
kind: Agent
metadata:
  name: lonely-agent
  version: 1.0.0
spec:
  model: model://none/1.0.0
  instructions: hi
"""
    )
    cp.register(agent, Principal.system())  # registered but not published
    with pytest.raises((NotFoundError, ResolutionError)):
        cp.resolve("agent://lonely-agent/1.0.0", "dev", Principal.system())


def test_missing_binding_raises(app):
    # Resolving in an environment with no bindings should fail with BINDING_MISSING.
    with pytest.raises(ResolutionError):
        app.resolve(AGENT_REF, environment="prod")
