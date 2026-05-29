from dataclasses import dataclass, asdict
from typing import Any


REQUIRED_INPUT_FIELDS = [
    "id",
    "source_type",
    "subject_or_title",
    "body_or_description",
    "sender_or_requester",
    "received_at",
]


@dataclass
class WorkItem:
    id: str
    source_type: str
    subject_or_title: str
    body_or_description: str
    sender_or_requester: str
    received_at: str
    tags: list[str]


@dataclass
class TriageRecord:
    id: str
    urgency: str
    category: str
    sentiment: str


@dataclass
class ActionItem:
    work_item_id: str
    summary: str
    owner: str | None
    deadline: str | None
    explicit_ask: str | None


@dataclass
class SuggestedResponse:
    work_item_id: str
    suggested_response: str


def to_dict(item: Any) -> dict[str, Any]:
    return asdict(item)
