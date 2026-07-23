"""HITLService - human-in-the-loop approvals.

Provides an approval gate strategies can call before a sensitive action. MVP1
stores approvals in-process with a configurable default decision (auto-approve in
dev). Production wires this to an approvals UI/workflow via domain events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from eap.common.events import DomainEvent, EventPublisher, EventType
from eap.common.ids import new_id


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ApprovalRequest:
    id: str
    run_id: str
    reason: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING


class HITLService:
    def __init__(self, events: EventPublisher, auto_approve: bool = True) -> None:
        self._events = events
        self._auto_approve = auto_approve
        self._requests: dict[str, ApprovalRequest] = {}

    def request(self, run_id: str, reason: str, payload: dict | None = None) -> ApprovalRequest:
        req = ApprovalRequest(
            id=new_id("appr"), run_id=run_id, reason=reason, payload=payload or {}
        )
        if self._auto_approve:
            req.status = ApprovalStatus.APPROVED
        self._requests[req.id] = req
        self._events.publish(
            DomainEvent(
                type=EventType.HITL_REQUESTED,
                payload={"id": req.id, "run_id": run_id, "reason": reason},
                correlation_id=run_id,
            )
        )
        return req

    def resolve(self, request_id: str, approved: bool) -> ApprovalRequest:
        req = self._requests[request_id]
        req.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        self._events.publish(
            DomainEvent(
                type=EventType.HITL_RESOLVED,
                payload={"id": req.id, "status": req.status.value},
                correlation_id=req.run_id,
            )
        )
        return req

    def get(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)
