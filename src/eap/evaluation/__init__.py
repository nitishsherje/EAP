"""Evaluation & Quality (Layer 1, cross-cutting).

Offline/online evaluation hooks, a regression scaffold, a lightweight
hallucination-detection hook, and human-feedback capture wired to the event bus
(observability). Kept decoupled from the runtime: evaluators operate on any object
exposing ``content`` and ``citations`` (see ``RunLike``), and the regression
runner takes a callable, so this module never imports an outer layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from eap.common.events import DomainEvent, EventPublisher, EventType
from eap.common.ids import new_id, now_iso


@runtime_checkable
class RunLike(Protocol):
    content: str
    citations: list[str]


# --------------------------------------------------------------------------- #
# Regression cases + evaluators                                               #
# --------------------------------------------------------------------------- #
@dataclass
class EvalCase:
    id: str
    ref: str
    query: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    expected_contains: list[str] = field(default_factory=list)
    expect_citations: bool = False


@dataclass
class EvalResult:
    case_id: str
    evaluator: str
    passed: bool
    score: float
    detail: str = ""


@dataclass
class EvalReport:
    results: list[EvalResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 1.0
        return round(sum(1 for r in self.results if r.passed) / len(self.results), 4)

    def failures(self) -> list[EvalResult]:
        return [r for r in self.results if not r.passed]


class Evaluator(ABC):
    name: str = "evaluator"

    @abstractmethod
    def evaluate(self, case: EvalCase, run: RunLike) -> EvalResult: ...


class NonEmptyEvaluator(Evaluator):
    name = "non_empty"

    def evaluate(self, case: EvalCase, run: RunLike) -> EvalResult:
        ok = bool(run.content and run.content.strip())
        return EvalResult(case.id, self.name, ok, 1.0 if ok else 0.0, "content present" if ok else "empty content")


class ContainsEvaluator(Evaluator):
    name = "contains"

    def evaluate(self, case: EvalCase, run: RunLike) -> EvalResult:
        if not case.expected_contains:
            return EvalResult(case.id, self.name, True, 1.0, "no expectations")
        found = [s for s in case.expected_contains if s.lower() in run.content.lower()]
        score = len(found) / len(case.expected_contains)
        ok = score == 1.0
        detail = f"matched {len(found)}/{len(case.expected_contains)}"
        return EvalResult(case.id, self.name, ok, round(score, 4), detail)


class CitationsEvaluator(Evaluator):
    name = "citations"

    def evaluate(self, case: EvalCase, run: RunLike) -> EvalResult:
        if not case.expect_citations:
            return EvalResult(case.id, self.name, True, 1.0, "not required")
        ok = bool(run.citations)
        return EvalResult(case.id, self.name, ok, 1.0 if ok else 0.0, f"{len(run.citations)} citations")


DEFAULT_EVALUATORS: list[Evaluator] = [NonEmptyEvaluator(), ContainsEvaluator(), CitationsEvaluator()]


def run_suite(
    runner: Callable[[EvalCase], RunLike],
    cases: list[EvalCase],
    evaluators: list[Evaluator] | None = None,
) -> EvalReport:
    """Run every case through ``runner`` and apply the evaluators. Offline harness."""
    evaluators = evaluators or DEFAULT_EVALUATORS
    report = EvalReport()
    for case in cases:
        run = runner(case)
        for evaluator in evaluators:
            report.results.append(evaluator.evaluate(case, run))
    return report


# --------------------------------------------------------------------------- #
# Hallucination detection hook                                                #
# --------------------------------------------------------------------------- #
@dataclass
class HallucinationSignal:
    flagged: bool
    reason: str = ""


def detect_hallucination(
    content: str, citations: list[str], *, require_grounding: bool = True
) -> HallucinationSignal:
    """Heuristic groundedness hook.

    MVP heuristic: if grounding is required and the response makes substantive
    claims but carries no citations, flag for review. Real deployments plug a
    grounding/NLI model behind this same signature.
    """
    substantive = len(content.strip()) > 40
    if require_grounding and substantive and not citations:
        return HallucinationSignal(True, "substantive response with no supporting citations")
    return HallucinationSignal(False)


# --------------------------------------------------------------------------- #
# Human feedback capture                                                      #
# --------------------------------------------------------------------------- #
@dataclass
class Feedback:
    id: str
    run_id: str
    rating: int  # e.g. -1, 0, +1 or 1..5
    comment: str = ""
    subject: str = "anonymous"
    recorded_at: str = field(default_factory=now_iso)


class FeedbackService:
    """Captures human feedback and emits it to the event bus for observability."""

    def __init__(self, events: EventPublisher) -> None:
        self._events = events
        self._store: list[Feedback] = []

    def record(self, run_id: str, rating: int, comment: str = "", subject: str = "anonymous") -> Feedback:
        fb = Feedback(id=new_id("fb"), run_id=run_id, rating=rating, comment=comment, subject=subject)
        self._store.append(fb)
        self._events.publish(
            DomainEvent(
                type=EventType.FEEDBACK_RECORDED,
                payload={"id": fb.id, "run_id": run_id, "rating": rating},
                correlation_id=run_id,
            )
        )
        return fb

    def for_run(self, run_id: str) -> list[Feedback]:
        return [f for f in self._store if f.run_id == run_id]

    def all(self) -> list[Feedback]:
        return list(self._store)


__all__ = [
    "CitationsEvaluator",
    "ContainsEvaluator",
    "DEFAULT_EVALUATORS",
    "EvalCase",
    "EvalReport",
    "EvalResult",
    "Evaluator",
    "Feedback",
    "FeedbackService",
    "HallucinationSignal",
    "NonEmptyEvaluator",
    "RunLike",
    "detect_hallucination",
    "run_suite",
]
