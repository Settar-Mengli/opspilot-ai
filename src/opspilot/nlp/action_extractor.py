import re

from opspilot.models.schemas import ActionItem, WorkItem

OWNER_PATTERN = re.compile(r"owner:\s*([A-Za-z][A-Za-z0-9 _-]{1,40})", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
ASK_PATTERN = re.compile(
    r"\b(please|can you|need you to|kindly|action required|follow up)\b",
    re.IGNORECASE,
)


def extract_action_items(item: WorkItem) -> list[ActionItem]:
    content = f"{item.subject_or_title} {item.body_or_description}"
    owner_match = OWNER_PATTERN.search(content)
    date_match = DATE_PATTERN.search(content)
    ask_match = ASK_PATTERN.search(content)

    owner = owner_match.group(1).strip() if owner_match else None
    deadline = date_match.group(1) if date_match else _phrase_deadline(content)
    explicit_ask = ask_match.group(1).lower() if ask_match else None

    if not owner and not deadline and not explicit_ask:
        return []

    return [
        ActionItem(
            work_item_id=item.id,
            summary=item.subject_or_title,
            owner=owner,
            deadline=deadline,
            explicit_ask=explicit_ask,
        )
    ]


def _phrase_deadline(content: str) -> str | None:
    lowered = content.lower()
    if "by eod" in lowered:
        return "EOD"
    if "by tomorrow" in lowered:
        return "tomorrow"
    if "this week" in lowered:
        return "this week"
    return None
