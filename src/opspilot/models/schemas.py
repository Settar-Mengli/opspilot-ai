from dataclasses import asdict, dataclass
from typing import Any

REQUIRED_INPUT_FIELDS = [
    "id",
    "source_type",
    "subject_or_title",
    "body_or_description",
    "sender_or_requester",
    "received_at",
]


class OpsPilotError(Exception):
    """Base exception for user-facing OpsPilot pipeline failures."""


class InputValidationError(OpsPilotError):
    """Raised when input data fails schema validation."""


class PipelineExecutionError(OpsPilotError):
    """Raised when orchestration fails after input validation."""


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
    urgency_reason: str
    category: str
    category_reason: str
    sentiment: str
    sentiment_reason: str


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


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_raw_item(item: dict[str, Any], idx: int) -> None:
    if not isinstance(item, dict):
        raise InputValidationError(f"Item at index {idx} is not an object")

    missing_fields = [key for key in REQUIRED_INPUT_FIELDS if key not in item]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise InputValidationError(f"Item {item.get('id', idx)} missing required fields: {missing}")

    for field in REQUIRED_INPUT_FIELDS:
        if not _is_non_empty_string(item.get(field)):
            raise InputValidationError(f"Item {item.get('id', idx)} field '{field}' must be a non-empty string")

    if "tags" in item and not isinstance(item["tags"], list):
        raise InputValidationError(f"Item {item.get('id', idx)} field 'tags' must be an array when provided")


def to_dict(item: Any) -> dict[str, Any]:
    return asdict(item)
