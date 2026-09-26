from opspilot.models.schemas import TriageRecord, WorkItem

URGENCY_LABELS = {"low", "medium", "high", "critical"}
CATEGORY_LABELS = {"incident", "request", "admin", "follow_up", "other"}
SENTIMENT_LABELS = {"negative", "neutral", "positive"}


def classify_work_item(item: WorkItem) -> TriageRecord:
    content = f"{item.subject_or_title} {item.body_or_description}".lower()
    urgency, urgency_reason = _classify_urgency(content)
    category, category_reason = _classify_category(content, item.source_type)
    sentiment, sentiment_reason = _classify_sentiment(content)

    return TriageRecord(
        id=item.id,
        urgency=urgency,
        urgency_reason=urgency_reason,
        category=category,
        category_reason=category_reason,
        sentiment=sentiment,
        sentiment_reason=sentiment_reason,
    )


def _first_match(content: str, tokens: list[str]) -> str | None:
    for token in tokens:
        if token in content:
            return token
    return None


def _classify_urgency(content: str) -> tuple[str, str]:
    critical_tokens = ["sev1", "production down", "outage", "security breach", "data loss"]
    high_tokens = ["urgent", "asap", "p1", "today", "by eod", "escalation"]
    medium_tokens = ["tomorrow", "this week", "follow up", "reminder"]

    matched = _first_match(content, critical_tokens)
    if matched:
        return "critical", f"Matched critical token '{matched}'"

    matched = _first_match(content, high_tokens)
    if matched:
        return "high", f"Matched high-priority token '{matched}'"

    matched = _first_match(content, medium_tokens)
    if matched:
        return "medium", f"Matched medium-priority token '{matched}'"

    return "low", "No urgency token matched; defaulted to low"


def _classify_category(content: str, source_type: str) -> tuple[str, str]:
    incident_tokens = ["incident", "error", "failed", "down", "outage", "bug"]
    request_tokens = ["request", "please", "approve", "provision", "access"]
    admin_tokens = ["invoice", "expense", "policy", "timesheet", "admin"]
    follow_up_tokens = ["follow up", "follow-up", "checking in", "reminder"]

    matched = _first_match(content, incident_tokens)
    if matched:
        return "incident", f"Matched incident token '{matched}'"

    matched = _first_match(content, request_tokens)
    if matched:
        return "request", f"Matched request token '{matched}'"

    matched = _first_match(content, admin_tokens)
    if matched:
        return "admin", f"Matched admin token '{matched}'"

    matched = _first_match(content, follow_up_tokens)
    if matched:
        return "follow_up", f"Matched follow-up token '{matched}'"

    if source_type == "support_request":
        return "request", "Defaulted to request for support_request source type"

    return "other", "No category token matched; defaulted to other"


def _classify_sentiment(content: str) -> tuple[str, str]:
    negative_tokens = ["frustrated", "angry", "blocked", "unhappy", "escalat", "broken"]
    positive_tokens = ["thanks", "thank you", "great", "appreciate", "good news"]

    matched = _first_match(content, negative_tokens)
    if matched:
        return "negative", f"Matched negative sentiment token '{matched}'"

    matched = _first_match(content, positive_tokens)
    if matched:
        return "positive", f"Matched positive sentiment token '{matched}'"

    return "neutral", "No sentiment token matched; defaulted to neutral"
