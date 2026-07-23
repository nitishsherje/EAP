from __future__ import annotations

import pytest

from eap.common.errors import SpecValidationError
from eap.specifications import SemVer, load_yaml, select_version
from eap.specifications.references import Reference, ReferenceError, Scheme
from eap.specifications.versioning import matches_constraint


def test_reference_parse_pinned():
    ref = Reference.parse("agent://auditor-report-agent/1.0.0")
    assert ref.scheme is Scheme.AGENT
    assert ref.name == "auditor-report-agent"
    assert ref.version == "1.0.0"
    assert ref.is_pinned


def test_reference_parse_unpinned():
    ref = Reference.parse("prompt://auditor-analysis")
    assert ref.version is None
    assert not ref.is_pinned


@pytest.mark.parametrize("bad", ["agent:/x", "unknown://x/1.0.0", "Agent://X", "://x"])
def test_reference_invalid(bad):
    with pytest.raises(ReferenceError):
        Reference.parse(bad)


def test_semver_ordering_and_selection():
    versions = [SemVer.parse(v) for v in ("1.0.0", "1.2.0", "2.0.0")]
    assert select_version(versions, None) == SemVer.parse("2.0.0")
    assert select_version(versions, "1") == SemVer.parse("1.2.0")
    assert select_version(versions, "1.0.0") == SemVer.parse("1.0.0")
    assert select_version(versions, "3") is None


def test_matches_constraint():
    assert matches_constraint(SemVer.parse("1.2.3"), "1")
    assert matches_constraint(SemVer.parse("1.2.3"), "1.2")
    assert not matches_constraint(SemVer.parse("1.2.3"), "1.3")


def test_agent_reference_scheme_validation():
    bad = """
apiVersion: eap.crisil/v1
kind: Agent
metadata:
  name: bad-agent
  version: 1.0.0
spec:
  model: skill://not-a-model/1.0.0
"""
    with pytest.raises(SpecValidationError):
        load_yaml(bad)


def test_unknown_spec_field_rejected():
    bad = """
apiVersion: eap.crisil/v1
kind: Skill
metadata:
  name: x
  version: 1.0.0
spec:
  model: model://m/1.0.0
  guardrails: policy://p/1.0.0
"""
    # 'guardrails' is an agent-only field; SkillSpec forbids extras.
    with pytest.raises(SpecValidationError):
        load_yaml(bad)
