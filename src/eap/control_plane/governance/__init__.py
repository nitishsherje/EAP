"""GovernanceService - policy evaluation, RBAC/ABAC, classification, audit.

Consumes the Principal produced by the security layer and the Policy resources
gathered during resolution. Produces authorization decisions and the flattened
EffectivePolicy the runtime enforces.
"""

from __future__ import annotations

import fnmatch

from eap.security import AuditLogger, DataClassification, Principal
from eap.specifications.policy import Effect, PolicySpec
from eap.specifications.resolved_definition import EffectivePolicy

_CLASSIFICATION_ORDER = {
    DataClassification.PUBLIC: 0,
    DataClassification.INTERNAL: 1,
    DataClassification.CONFIDENTIAL: 2,
    DataClassification.RESTRICTED: 3,
}


class PolicyEvaluator:
    """Evaluates RBAC/ABAC statements. Explicit deny wins; default deny."""

    def evaluate(
        self,
        statements: list,  # list[PolicyStatement]
        principal: Principal,
        action: str,
        resource: str,
    ) -> bool:
        allowed = False
        for stmt in statements:
            if action not in stmt.actions and "*" not in stmt.actions:
                continue
            if not any(fnmatch.fnmatch(resource, pat) for pat in stmt.resources):
                continue
            if not self._conditions_met(stmt.conditions, principal):
                continue
            if stmt.effect == Effect.DENY:
                return False
            allowed = True
        return allowed

    @staticmethod
    def _conditions_met(conditions: dict, principal: Principal) -> bool:
        for key, expected in conditions.items():
            if key == "role":
                if expected not in principal.roles:
                    return False
            elif key == "tenant":
                if principal.tenant != expected:
                    return False
            elif principal.attributes.get(key) != str(expected):
                return False
        return True


class GovernanceService:
    def __init__(
        self,
        audit: AuditLogger,
        evaluator: PolicyEvaluator | None = None,
        enforce: bool = False,
    ) -> None:
        self._audit = audit
        self._evaluator = evaluator or PolicyEvaluator()
        # When False (dev), authorization is permissive but still audited.
        self._enforce = enforce

    def authorize(
        self,
        principal: Principal,
        action: str,
        resource: str,
        statements: list | None = None,
    ) -> bool:
        if not self._enforce:
            self._audit.record(action, principal, resource, enforced=False, decision="allow")
            return True
        decision = self._evaluator.evaluate(statements or [], principal, action, resource)
        self._audit.record(action, principal, resource, enforced=True, decision="allow" if decision else "deny")
        return decision

    def classify(self, classifications: list[str]) -> DataClassification:
        """Return the highest (most sensitive) classification present."""
        best = DataClassification.PUBLIC
        for raw in classifications:
            try:
                level = DataClassification(raw)
            except ValueError:
                continue
            if _CLASSIFICATION_ORDER[level] > _CLASSIFICATION_ORDER[best]:
                best = level
        return best

    def build_effective_policy(
        self,
        policies: list[PolicySpec],
        classifications: list[str],
        required_scopes: list[str],
    ) -> EffectivePolicy:
        guardrails: list[dict] = []
        for policy in policies:
            guardrails.extend(g.model_dump() for g in policy.guardrails)
            classifications.append(policy.data_classification)
        return EffectivePolicy(
            data_classification=self.classify(classifications).value,
            guardrails=guardrails,
            required_scopes=sorted(set(required_scopes)),
        )
