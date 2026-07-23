"""WorkflowStrategy - coordinates multi-step execution.

Supports sequential/graph execution via topological ordering of ``depends_on``.
Step types: skill (deterministic capability calls) and agent (delegated to the
shared agent runner). Nested-workflow steps are not expanded in MVP1. Placeholders
of the form ``${input.x}`` and ``${step_id.output[.field]}`` are resolved between
steps.
"""

from __future__ import annotations

import re
from typing import Any

from eap.common.errors import ExecutionError
from eap.runtime.agent_runner import run_agent
from eap.runtime.context import ExecutionContext
from eap.runtime.deps import RuntimeServices
from eap.runtime.models import ExecutionResult, ToolCall
from eap.runtime.strategies.base import ExecutionStrategy
from eap.specifications.agent import Agent
from eap.specifications.skill import Skill, SkillType
from eap.specifications.workflow import StepType, Workflow

_PLACEHOLDER = re.compile(r"^\$\{([^}]+)\}$")


class WorkflowStrategy(ExecutionStrategy):
    name = "workflow"

    def execute(self, ctx: ExecutionContext, services: RuntimeServices) -> ExecutionResult:
        rd = ctx.rd
        request = ctx.request
        workflow = rd.root_workflow
        if not isinstance(workflow, Workflow):
            raise ExecutionError("WorkflowStrategy requires a workflow root")

        order = self._topo_order(workflow)
        scope: dict[str, Any] = {"input": request.inputs}
        step_outputs: dict[str, Any] = {}
        tool_calls: list[ToolCall] = []
        citations: list[str] = []
        prompt_tokens = completion_tokens = 0
        last_content = ""

        for step_id in order:
            step = next(s for s in workflow.spec.steps if s.id == step_id)
            resolved_inputs = {
                k: self._resolve(v, scope, step_outputs) for k, v in step.inputs.items()
            }

            if step.type == StepType.SKILL:
                output, calls = self._run_skill(rd, services, step.ref, resolved_inputs)
                tool_calls.extend(calls)
                step_outputs[step_id] = output
            elif step.type == StepType.AGENT:
                agent = rd.bundle.agents.get(rd.pin(step.ref))
                if not isinstance(agent, Agent):
                    raise ExecutionError(f"agent {step.ref} not in resolved definition")
                outcome = run_agent(
                    rd,
                    agent,
                    services,
                    request,
                    instructions=agent.spec.instructions or "",
                    query=request.query,
                    inputs=resolved_inputs,
                )
                tool_calls.extend(outcome.tool_calls)
                citations.extend(outcome.citations)
                prompt_tokens += outcome.prompt_tokens
                completion_tokens += outcome.completion_tokens
                last_content = outcome.content
                step_outputs[step_id] = {
                    "content": outcome.content,
                    "structured": outcome.structured,
                }
            else:  # nested workflow
                raise ExecutionError(
                    f"nested workflow step '{step_id}' is not supported in MVP1"
                )
            scope[step_id] = {"output": step_outputs[step_id]}

        # Emit outputs from the declared output_targets (fall back to last step).
        targets = workflow.spec.output_targets or ([order[-1]] if order else [])
        output = {t: step_outputs.get(t) for t in targets}
        return ExecutionResult(
            run_id=request.run_id,
            status="succeeded",
            output={"steps": step_outputs, "targets": output},
            content=last_content,
            citations=list(dict.fromkeys(citations)),
            tool_calls=tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    # --- step execution ---
    def _run_skill(self, rd, services, skill_ref, inputs):  # noqa: ANN001
        skill = rd.bundle.skills.get(rd.pin(skill_ref))
        if not isinstance(skill, Skill):
            raise ExecutionError(f"skill {skill_ref} not in resolved definition")
        output: dict[str, Any] = {}
        calls: list[ToolCall] = []
        if skill.spec.type != SkillType.DETERMINISTIC:
            # Agentic/function skills would be delegated to the framework; MVP1 runs
            # deterministic skills directly.
            return output, calls
        for use in skill.spec.capabilities:
            if not use.operation:
                continue
            result = services.capability_manager.invoke(rd, use.ref, use.operation, inputs)
            calls.append(
                ToolCall(
                    capability=result.capability,
                    operation=result.operation,
                    ok=result.ok,
                    summary=str(result.output)[:200] if result.ok else (result.error or ""),
                )
            )
            if result.ok:
                output[use.operation] = result.output
        return output, calls

    # --- helpers ---
    @staticmethod
    def _topo_order(workflow: Workflow) -> list[str]:
        graph = {s.id: list(s.depends_on) for s in workflow.spec.steps}
        order: list[str] = []
        visited: set[str] = set()

        def visit(node: str, stack: set[str]) -> None:
            if node in visited:
                return
            if node in stack:
                raise ExecutionError(f"cycle detected at step '{node}'")
            stack.add(node)
            for dep in graph.get(node, []):
                visit(dep, stack)
            stack.discard(node)
            visited.add(node)
            order.append(node)

        for step in workflow.spec.steps:
            visit(step.id, set())
        return order

    def _resolve(self, value: Any, scope: dict, step_outputs: dict) -> Any:
        if not isinstance(value, str):
            return value
        match = _PLACEHOLDER.match(value)
        if not match:
            return value
        path = match.group(1).split(".")
        cursor: Any = scope
        for part in path:
            if isinstance(cursor, dict) and part in cursor:
                cursor = cursor[part]
            else:
                return value  # unresolved -> leave as-is
        return cursor
