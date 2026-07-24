from __future__ import annotations

import pytest

from eap.api_gateway.assembly import build_app_with_examples

AGENT_REF = "agent://auditor-report-agent/1.0.0"


@pytest.fixture
def app():
    return build_app_with_examples()
