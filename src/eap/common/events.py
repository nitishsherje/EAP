"""Event abstraction (Layer 0).

Per the baseline eventing principle: define the abstraction now, ship an
in-process implementation, and introduce Kafka/MSK only when a concrete
requirement (high-volume async, independent consumers, replay, durability)
justifies it.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from eap.common.ids import new_id, now_iso


@dataclass(frozen=True)
class DomainEvent:
    """An immutable fact about something that happened in the platform."""

    type: str
    payload: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("evt"))
    occurred_at: str = field(default_factory=now_iso)
    correlation_id: str | None = None


EventHandler = Callable[[DomainEvent], None]


@runtime_checkable
class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...


@runtime_checkable
class EventSubscriber(Protocol):
    def subscribe(self, event_type: str, handler: EventHandler) -> None: ...


class InProcessEventBus(EventPublisher, EventSubscriber):
    """Default synchronous, single-process publisher + subscriber.

    Handler exceptions are swallowed (best-effort delivery) so that a faulty
    observer cannot break the primary execution path.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(event.type, []):
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - observers must not break producers
                continue


# Well-known event types.
class EventType:
    SPEC_REGISTERED = "spec.registered"
    SPEC_PUBLISHED = "spec.published"
    SPEC_DEPRECATED = "spec.deprecated"
    AGENT_RESOLVED = "agent.resolved"
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    HITL_REQUESTED = "hitl.requested"
    HITL_RESOLVED = "hitl.resolved"
    FEEDBACK_RECORDED = "feedback.recorded"
