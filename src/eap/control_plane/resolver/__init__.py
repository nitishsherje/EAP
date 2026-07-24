"""Resolver - turns a logical reference into an immutable ResolvedDefinition.

This is the producer side of the critical ResolvedDefinition boundary:

    Validate -> Register -> Resolve refs -> Pin versions -> Bind environment
      -> Apply governance/policies -> Integrity hash -> ResolvedDefinition

Nothing executes until this has run. The resolver walks the full dependency
graph of an agent or workflow, pins every reference to a concrete version,
inlines the environment bindings, and captures the effective policy.
"""

from __future__ import annotations

from eap.common.errors import ErrorCode, ResolutionError
from eap.control_plane.governance import GovernanceService
from eap.control_plane.registry import Registry
from eap.security import Principal
from eap.specifications.agent import Agent
from eap.specifications.binding import CapabilityBinding
from eap.specifications.capability import Capability, Protocol
from eap.specifications.envelope import ResourceKind
from eap.specifications.knowledge import Knowledge
from eap.specifications.model_profile import ModelProfile
from eap.specifications.output_schema import OutputSchema
from eap.specifications.policy import Policy
from eap.specifications.prompt import Prompt
from eap.specifications.references import Reference, Scheme
from eap.specifications.resolved_definition import (
    Provenance,
    ResolvedBundle,
    ResolvedDefinition,
)
from eap.specifications.skill import Skill
from eap.specifications.versioning import SemVer, matches_constraint
from eap.specifications.workflow import Workflow

# Resource kinds that require an environment binding to be executable.
_BINDABLE_SCHEMES = {Scheme.CAPABILITY, Scheme.KNOWLEDGE, Scheme.MODEL}


class Resolver:
    def __init__(self, registry: Registry, governance: GovernanceService) -> None:
        self._registry = registry
        self._governance = governance

    def resolve(
        self,
        ref: str,
        environment: str = "dev",
        principal: Principal | None = None,
        *,
        published_only: bool = True,
    ) -> ResolvedDefinition:
        principal = principal or Principal.system()
        root = Reference.parse(ref)
        if root.scheme not in (Scheme.AGENT, Scheme.WORKFLOW):
            raise ResolutionError(
                f"can only resolve agent:// or workflow:// references, got {root.scheme.value}://",
                code=ErrorCode.RESOLUTION_FAILED,
            )

        ctx = _ResolutionContext(
            registry=self._registry,
            environment=environment,
            published_only=published_only,
        )
        pinned_root = ctx.resolve_ref(ref)

        # Governance: build effective policy and authorize the resolve action.
        effective = self._governance.build_effective_policy(
            policies=ctx.policies,
            classifications=ctx.classifications,
            required_scopes=ctx.required_scopes,
        )
        statements = [s for p in ctx.policies for s in p.statements]
        if not self._governance.authorize(principal, "resolve", pinned_root, statements):
            raise ResolutionError(
                f"resolve denied by policy for {pinned_root}", code=ErrorCode.POLICY_DENIED
            )

        root_kind = ResourceKind.AGENT if root.scheme == Scheme.AGENT else ResourceKind.WORKFLOW
        definition = ResolvedDefinition(
            environment=environment,
            target=pinned_root,
            root_kind=root_kind,
            bundle=ctx.bundle,
            effective_policy=effective,
            provenance=Provenance(requested_by=principal.subject, source_ref=ref),
        )
        return definition.finalize()


class _ResolutionContext:
    """Mutable accumulator used during a single resolve() call."""

    def __init__(self, registry: Registry, environment: str, published_only: bool) -> None:
        self._registry = registry
        self._environment = environment
        self._published_only = published_only
        self.bundle = ResolvedBundle()
        self.policies: list = []  # list[PolicySpec]
        self.classifications: list[str] = []
        self.required_scopes: list[str] = []
        self._seen: set[str] = set()

    def resolve_ref(self, ref_str: str) -> str:
        """Resolve, pin, bind and recurse. Returns the pinned reference string."""
        ref = Reference.parse(ref_str)
        record = self._registry.resolve(ref, published_only=self._published_only)
        resource = record.resource
        pinned = str(resource.ref)
        self.bundle.resolution_map[ref_str] = pinned
        self.bundle.resolution_map[pinned] = pinned

        if pinned in self._seen:
            return pinned
        self._seen.add(pinned)

        self._add_to_bundle(resource, pinned)
        return pinned

    def _add_to_bundle(self, resource, pinned: str) -> None:  # noqa: ANN001, C901
        if isinstance(resource, Agent):
            self.bundle.agents[pinned] = resource
            self._recurse_agent(resource)
        elif isinstance(resource, Workflow):
            self.bundle.workflows[pinned] = resource
            self._recurse_workflow(resource)
        elif isinstance(resource, Skill):
            self.bundle.skills[pinned] = resource
            self._recurse_skill(resource)
        elif isinstance(resource, Capability):
            self.bundle.capabilities[pinned] = resource
            self._bind_and_scope(resource, pinned)
        elif isinstance(resource, Knowledge):
            self.bundle.knowledge[pinned] = resource
            self.classifications.append(resource.spec.classification)
            self._require_binding(pinned)
        elif isinstance(resource, ModelProfile):
            self.bundle.models[pinned] = resource
            self._require_binding(pinned)
            for fb in resource.spec.fallback:
                self.resolve_ref(fb)
        elif isinstance(resource, Prompt):
            self.bundle.prompts[pinned] = resource
        elif isinstance(resource, Policy):
            self.bundle.policies[pinned] = resource.spec.model_dump()
            self.policies.append(resource.spec)
        elif isinstance(resource, OutputSchema):
            self.bundle.output_schemas[pinned] = resource

    def _recurse_agent(self, agent: Agent) -> None:
        spec = agent.spec
        self.resolve_ref(spec.model)
        if spec.prompt:
            self.resolve_ref(spec.prompt)
        if spec.guardrails:
            self.resolve_ref(spec.guardrails)
        if spec.output_schema:
            self.resolve_ref(spec.output_schema)
        for skill_ref in spec.skills:
            self.resolve_ref(skill_ref)
        for cap_ref in spec.capabilities:
            self.resolve_ref(cap_ref)
        for know_ref in spec.knowledge:
            self.resolve_ref(know_ref)

    def _recurse_workflow(self, workflow: Workflow) -> None:
        for step in workflow.spec.steps:
            self.resolve_ref(step.ref)

    def _recurse_skill(self, skill: Skill) -> None:
        spec = skill.spec
        if spec.model:
            self.resolve_ref(spec.model)
        if spec.prompt:
            self.resolve_ref(spec.prompt)
        if spec.output_schema:
            self.resolve_ref(spec.output_schema)
        for cap_use in spec.capabilities:
            self.resolve_ref(cap_use.ref)
        for know_ref in spec.knowledge:
            self.resolve_ref(know_ref)

    def _bind_and_scope(self, capability: Capability, pinned: str) -> None:
        self.classifications.append(capability.spec.classification)
        self.required_scopes.extend(capability.spec.required_scopes)
        # Native capabilities run in-process and need no external binding.
        if capability.spec.protocol != Protocol.NATIVE:
            self._require_binding(pinned)

    def _require_binding(self, pinned: str) -> None:
        binding = self._find_binding(pinned)
        if binding is None:
            raise ResolutionError(
                f"no CapabilityBinding for {pinned} in environment '{self._environment}'",
                code=ErrorCode.BINDING_MISSING,
            )
        self.bundle.bindings[pinned] = binding

    def _find_binding(self, pinned: str) -> CapabilityBinding | None:
        target = Reference.parse(pinned)
        records = self._registry.list(ResourceKind.CAPABILITY_BINDING)
        for record in records:
            binding = record.resource
            assert isinstance(binding, CapabilityBinding)
            if binding.spec.environment != self._environment:
                continue
            bt = binding.target_ref
            if bt.scheme != target.scheme or bt.name != target.name:
                continue
            if bt.version is None:
                return binding
            if SemVer.is_valid(bt.version):
                if bt.version == target.version:
                    return binding
            elif target.version and matches_constraint(SemVer.parse(target.version), bt.version):
                return binding
        return None
