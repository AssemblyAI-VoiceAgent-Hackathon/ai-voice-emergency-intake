"""In-memory case registry, event log, and idempotency map."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .auth import new_event_id
from .errors import ApiError

log = logging.getLogger("aria.backend")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class CaseEvent:
    event_id: str
    event_type: str
    case_id: str
    case_version: int
    occurred_at: str
    data: dict[str, Any]

    def envelope(self) -> dict[str, Any]:
        return {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "caseId": self.case_id,
            "caseVersion": self.case_version,
            "occurredAt": self.occurred_at,
            "data": self.data,
        }


@dataclass
class CaseRecord:
    case_id: str
    session_id: Optional[str] = None
    case_version: int = -1
    structured_case: Optional[dict[str, Any]] = None
    review_status: str = "none"
    protected_edits: list[dict[str, Any]] = field(default_factory=list)
    events: list[CaseEvent] = field(default_factory=list)
    ingest_keys: dict[str, dict[str, Any]] = field(default_factory=dict)
    review_keys: dict[str, dict[str, Any]] = field(default_factory=dict)
    tool_keys: dict[str, dict[str, Any]] = field(default_factory=dict)
    linked_patient_public_id: Optional[str] = None
    linked_phone: Optional[str] = None
    persistence_case_id: Optional[int] = None
    approved: bool = False


class CaseRegistry:
    def __init__(self) -> None:
        self._cases: dict[str, CaseRecord] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def get(self, case_id: str) -> CaseRecord:
        record = self._cases.get(case_id)
        if record is None:
            raise ApiError(404, "CASE_NOT_FOUND", "The case was not found.")
        return record

    def get_or_create(self, case_id: str) -> CaseRecord:
        if case_id not in self._cases:
            self._cases[case_id] = CaseRecord(case_id=case_id)
        return self._cases[case_id]

    def snapshot(self, record: CaseRecord) -> dict[str, Any]:
        return {
            "caseId": record.case_id,
            "sessionId": record.session_id,
            "caseVersion": record.case_version,
            "reviewStatus": record.review_status,
            "structuredCase": deepcopy(record.structured_case),
            "linkedPatientPublicId": record.linked_patient_public_id,
        }

    def list_ready(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for record in reversed(list(self._cases.values())):
            if record.structured_case is None:
                continue
            summary = (record.structured_case.get("summary") or {}).get("oneLine")
            items.append(
                {
                    "caseId": record.case_id,
                    "sessionId": record.session_id,
                    "caseVersion": record.case_version,
                    "reviewStatus": record.review_status,
                    "status": record.structured_case.get("status"),
                    "summary": summary,
                }
            )
        return items

    def publish(self, record: CaseRecord, event_type: str, data: dict[str, Any]) -> CaseEvent:
        event = CaseEvent(
            event_id=new_event_id(),
            event_type=event_type,
            case_id=record.case_id,
            case_version=record.case_version,
            occurred_at=utc_now(),
            data=data,
        )
        record.events.append(event)
        log.info(
            "sse_event event_type=%s case_id=%s case_version=%s event_id=%s",
            event_type,
            record.case_id,
            record.case_version,
            event.event_id,
        )
        for queue in list(self._subscribers.get(record.case_id, [])):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                continue
        return event

    def events_after(self, record: CaseRecord, last_event_id: Optional[str]) -> list[CaseEvent]:
        if not last_event_id:
            return list(record.events)
        index = next((i for i, event in enumerate(record.events) if event.event_id == last_event_id), None)
        if index is None:
            return list(record.events)
        return record.events[index + 1 :]

    def subscribe(self, case_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.setdefault(case_id, []).append(queue)
        return queue

    def unsubscribe(self, case_id: str, queue: asyncio.Queue) -> None:
        listeners = self._subscribers.get(case_id, [])
        if queue in listeners:
            listeners.remove(queue)
