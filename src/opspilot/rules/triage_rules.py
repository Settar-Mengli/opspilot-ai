from opspilot.models.schemas import TriageRecord, WorkItem


URGENCY_LABELS = {"low", "medium", "high", "critical"}
CATEGORY_LABELS = {"incident", "request", "admin", "follow_up", "other"}
SENTIMENT_LABELS = {"negative", "neutral", "positive"}


def classify_work_item(item: WorkItem) -> TriageRecord:
    content = f"{item.subject_or_title} {item.body_or_description}".lower()
    return TriageRecord(
        id=item.id,
        urgency=_classify_urgency(content),
        category=_classify_category(content, item.source_type),
        sentiment=_classify_sentiment(content),
    )


def _classify_urgency(content: str) -> str:
    critical_tokens = ["sev1", "production down", "outage", "security breach", "data loss"]
    high_tokens = ["urgent", "asap", "p1", "today", "by eod", "escalation"]
    medium_tokens = ["tomorrow", "this week", "follow up", "reminder"]

    if any(token in content for token in critical_tokens):
        return "critical"
    if any(token in content for token in high_tokens):
        return "high"
    if any(token in content for token in medium_tokens):
        return "medium"
    return "low"


def _classify_category(content: str, source_type: str) -> str:
    incident_tokens = ["incident", "error", "failed", "down", "outage", "bug"]
    request_tokens = ["request", "please", "approve", "provision", "access"]
    admin_tokens = ["invoice", "expense", "policy", "timesheet", "admin"]
    follow_up_tokens = ["follow up", "follow-up", "checking in", "reminder"]

    if any(token in content for token in incident_tokens):
        return "incident"
    if any(token in content for token in request_tokens):
        return "request"
    if any(token in content for token in admin_tokens):
        return "admin"
    if any(token in content for token in follow_up_tokens):
        return "follow_up"
    if source_type == "support_request":
        return "request"
    return "other"


def _classify_sentiment(content: str) -> str:
    negative_tokens = ["frustrated", "angry", "blocked", "unhappy", "escalat", "broken"]
    positive_tokens = ["thanks", "thank you", "great", "appreciate", "good news"]

    if any(token in content for token in negative_tokens):
        return "negative"
    if any(token in content for token in positive_tokens):
        return "positive"
    return "neutral"
