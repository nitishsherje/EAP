"""SpecificationService - ingestion + validation.

Validation layers (all issues collected, not fail-fast):
    1. Schema     - structural (enforced by the Pydantic models on parse)
    2. Semantic   - kind-specific rules (this module)
    3. Reference  - reference strings well-formed (enforced by field validators)
    4. Compatibility - version monotonicity vs. previously registered versions
"""

from __future__ import annotations

from eap.common.errors import ErrorCode, ValidationResult
from eap.control_plane.registry import Registry
from eap.persistence.models import LifecycleStatus, ResourceRecord
from eap.security import Principal
from eap.specifications.agent import Agent
from eap.specifications.capability import Capability
from eap.specifications.envelope import EapResource
from eap.specifications.knowledge import Knowledge
from eap.specifications.model_profile import ModelProfile
from eap.specifications.skill import Skill, SkillType
from eap.specifications.versioning import SemVer
from eap.specifications.workflow import Workflow


class SpecificationService:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    # --- validation ---
    def validate(self, resource: EapResource) -> ValidationResult:
        result = ValidationResult()
        self._validate_semantic(resource, result)
        self._validate_compatibility(resource, result)
        return result

    def _validate_semantic(self, resource: EapResource, result: ValidationResult) -> None:
        if isinstance(resource, Agent):
            self._validate_agent(resource, result)
        elif isinstance(resource, Workflow):
            self._validate_workflow(resource, result)
        elif isinstance(resource, Skill):
            self._validate_skill(resource, result)
        elif isinstance(resource, Capability):
            self._validate_capability(resource, result)
        elif isinstance(resource, Knowledge):
            self._validate_knowledge(resource, result)
        elif isinstance(resource, ModelProfile):
            self._validate_model(resource, result)

    def _validate_agent(self, agent: Agent, result: ValidationResult) -> None:
        spec = agent.spec
        if agent.spec.max_iterations < 1:
            result.error(ErrorCode.SEMANTIC_INVALID, "max_iterations must be >= 1", "spec.max_iterations")
        if not spec.instructions and not spec.prompt:
            result.warn(
                ErrorCode.SEMANTIC_INVALID,
                "agent has neither inline instructions nor a prompt reference",
                "spec",
            )
        if not spec.skills and not spec.capabilities:
            result.warn(
                ErrorCode.SEMANTIC_INVALID,
                "agent has no skills or capabilities; it can only reason with the model",
                "spec",
            )

    def _validate_workflow(self, workflow: Workflow, result: ValidationResult) -> None:
        steps = workflow.spec.steps
        ids = {s.id for s in steps}
        for step in steps:
            for dep in step.depends_on:
                if dep not in ids:
                    result.error(
                        ErrorCode.SEMANTIC_INVALID,
                        f"step '{step.id}' depends on unknown step '{dep}'",
                        f"spec.steps.{step.id}.depends_on",
                    )
        for target in workflow.spec.output_targets:
            if target not in ids:
                result.error(
                    ErrorCode.SEMANTIC_INVALID,
                    f"output_target '{target}' is not a defined step id",
                    "spec.output_targets",
                )
        if self._has_cycle(steps):
            result.error(ErrorCode.SEMANTIC_INVALID, "workflow dependency graph has a cycle", "spec.steps")

    @staticmethod
    def _has_cycle(steps) -> bool:  # noqa: ANN001
        graph = {s.id: set(s.depends_on) for s in steps}
        visited: set[str] = set()
        stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            stack.add(node)
            for dep in graph.get(node, ()):  # dep must exist in graph
                if dep not in graph:
                    continue
                if dep in stack:
                    return True
                if dep not in visited and dfs(dep):
                    return True
            stack.discard(node)
            return False

        return any(node not in visited and dfs(node) for node in graph)

    def _validate_skill(self, skill: Skill, result: ValidationResult) -> None:
        spec = skill.spec
        if spec.type == SkillType.DETERMINISTIC and not spec.capabilities:
            result.warn(
                ErrorCode.SEMANTIC_INVALID,
                "deterministic skill has no capabilities to invoke",
                "spec.capabilities",
            )
        if spec.type == SkillType.AGENTIC and not spec.model:
            result.warn(
                ErrorCode.SEMANTIC_INVALID,
                "agentic skill should reference a model",
                "spec.model",
            )

    def _validate_capability(self, capability: Capability, result: ValidationResult) -> None:
        names = [op.name for op in capability.spec.operations]
        if len(names) != len(set(names)):
            result.error(ErrorCode.SEMANTIC_INVALID, "operation names must be unique", "spec.operations")

    def _validate_knowledge(self, knowledge: Knowledge, result: ValidationResult) -> None:
        if knowledge.spec.top_k < 1:
            result.error(ErrorCode.SEMANTIC_INVALID, "top_k must be >= 1", "spec.top_k")

    def _validate_model(self, model: ModelProfile, result: ValidationResult) -> None:
        self_ref = f"model://{model.metadata.name}"
        for fb in model.spec.fallback:
            if fb.startswith(self_ref):
                result.error(
                    ErrorCode.SEMANTIC_INVALID,
                    "model profile cannot list itself as a fallback",
                    "spec.fallback",
                )

    def _validate_compatibility(self, resource: EapResource, result: ValidationResult) -> None:
        existing = self._registry.list_versions(resource.kind, resource.metadata.name)
        if not existing:
            return
        newest = existing[0]
        candidate = SemVer.parse(resource.metadata.version)
        if candidate in existing:
            result.error(
                ErrorCode.COMPATIBILITY_BROKEN,
                f"version {candidate} already registered (versions are immutable)",
                "metadata.version",
            )
        elif candidate < newest:
            result.warn(
                ErrorCode.COMPATIBILITY_BROKEN,
                f"registering {candidate} which is older than latest {newest} (backport?)",
                "metadata.version",
            )

    # --- ingestion ---
    def ingest(
        self,
        resource: EapResource,
        principal: Principal | None = None,
        status: LifecycleStatus = LifecycleStatus.DRAFT,
    ) -> ResourceRecord:
        """Validate then register a resource. Raises SpecValidationError on failure."""
        self.validate(resource).raise_if_failed()
        return self._registry.register(resource, status=status)
