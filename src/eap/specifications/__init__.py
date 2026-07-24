"""Specification Layer (Layer 0).

Executable Pydantic implementation of the frozen EAP Specification Contract v1.0.
Pure domain: this package imports only ``eap.common`` and third-party libraries,
never any outer EAP layer.
"""

from eap.specifications.agent import Agent, AgentSpec
from eap.specifications.binding import AuthBinding, BindingSpec, CapabilityBinding
from eap.specifications.capability import (
    Capability,
    CapabilitySpec,
    Operation,
    Protocol,
)
from eap.specifications.envelope import (
    API_VERSION,
    EapResource,
    Metadata,
    ResourceKind,
)
from eap.specifications.knowledge import Knowledge, KnowledgeSpec, RetrievalStrategy
from eap.specifications.loader import (
    KIND_MODELS,
    load_file,
    load_yaml,
    load_yaml_documents,
    parse_resource,
    to_model,
)
from eap.specifications.model_profile import ModelProfile, ModelProfileSpec
from eap.specifications.output_schema import OutputSchema, OutputSchemaSpec
from eap.specifications.policy import Policy, PolicySpec
from eap.specifications.prompt import Prompt, PromptSpec
from eap.specifications.references import Reference, ReferenceError, Scheme
from eap.specifications.resolved_definition import (
    EffectivePolicy,
    Provenance,
    ResolvedBundle,
    ResolvedDefinition,
)
from eap.specifications.skill import Skill, SkillSpec, SkillType
from eap.specifications.versioning import Compatibility, SemVer, select_version
from eap.specifications.workflow import Workflow, WorkflowPattern, WorkflowSpec

__all__ = [
    "API_VERSION",
    "KIND_MODELS",
    "Agent",
    "AgentSpec",
    "AuthBinding",
    "BindingSpec",
    "Capability",
    "CapabilityBinding",
    "CapabilitySpec",
    "Compatibility",
    "EapResource",
    "EffectivePolicy",
    "Knowledge",
    "KnowledgeSpec",
    "Metadata",
    "ModelProfile",
    "ModelProfileSpec",
    "Operation",
    "OutputSchema",
    "OutputSchemaSpec",
    "Policy",
    "PolicySpec",
    "Prompt",
    "PromptSpec",
    "Protocol",
    "Provenance",
    "Reference",
    "ReferenceError",
    "ResolvedBundle",
    "ResolvedDefinition",
    "ResourceKind",
    "RetrievalStrategy",
    "Scheme",
    "SemVer",
    "Skill",
    "SkillSpec",
    "SkillType",
    "Workflow",
    "WorkflowPattern",
    "WorkflowSpec",
    "load_file",
    "load_yaml",
    "load_yaml_documents",
    "parse_resource",
    "select_version",
    "to_model",
]
