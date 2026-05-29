from opspilot.models.schemas import WorkItem
from opspilot.rules.triage_rules import classify_work_item


def test_classifier_critical_incident_negative() -> None:
    item = WorkItem(
        id="WI-X",
        source_type="email",
        subject_or_title="Production outage",
        body_or_description="Sev1 outage and customers are frustrated",
        sender_or_requester="ops@local",
        received_at="2026-05-29T00:00:00Z",
        tags=[],
    )

    triage = classify_work_item(item)
    assert triage.urgency == "critical"
    assert triage.urgency_reason == "Matched critical token 'sev1'"
    assert triage.category == "incident"
    assert triage.category_reason == "Matched incident token 'outage'"
    assert triage.sentiment == "negative"
    assert triage.sentiment_reason == "Matched negative sentiment token 'frustrated'"


def test_classifier_request_positive() -> None:
    item = WorkItem(
        id="WI-Y",
        source_type="support_request",
        subject_or_title="Access request",
        body_or_description="Please provision access. Thank you and appreciate your help.",
        sender_or_requester="helpdesk@local",
        received_at="2026-05-29T00:00:00Z",
        tags=[],
    )

    triage = classify_work_item(item)
    assert triage.urgency in {"low", "medium", "high", "critical"}
    assert triage.urgency_reason == "No urgency token matched; defaulted to low"
    assert triage.category == "request"
    assert triage.category_reason == "Matched request token 'request'"
    assert triage.sentiment == "positive"
    assert triage.sentiment_reason == "Matched positive sentiment token 'thank you'"

    triage_again = classify_work_item(item)
    assert triage.urgency_reason == triage_again.urgency_reason
    assert triage.category_reason == triage_again.category_reason
    assert triage.sentiment_reason == triage_again.sentiment_reason
