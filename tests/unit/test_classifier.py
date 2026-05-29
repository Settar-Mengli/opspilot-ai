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
    assert triage.category == "incident"
    assert triage.sentiment == "negative"


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
    assert triage.category == "request"
    assert triage.sentiment == "positive"
