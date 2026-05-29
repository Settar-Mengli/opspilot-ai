from opspilot.models.schemas import WorkItem
from opspilot.nlp.action_extractor import extract_action_items


def test_extracts_owner_deadline_and_ask() -> None:
    item = WorkItem(
        id="WI-A",
        source_type="task",
        subject_or_title="Access task",
        body_or_description="Please grant access by 2026-05-30. owner: IT Ops",
        sender_or_requester="ops@local",
        received_at="2026-05-29T00:00:00Z",
        tags=[],
    )

    actions = extract_action_items(item)
    assert len(actions) == 1
    assert actions[0].work_item_id == "WI-A"
    assert actions[0].owner == "IT Ops"
    assert actions[0].deadline == "2026-05-30"
    assert actions[0].explicit_ask == "please"


def test_returns_empty_when_no_action_signal() -> None:
    item = WorkItem(
        id="WI-B",
        source_type="task",
        subject_or_title="Status update",
        body_or_description="General status update with no request language.",
        sender_or_requester="ops@local",
        received_at="2026-05-29T00:00:00Z",
        tags=[],
    )

    actions = extract_action_items(item)
    assert actions == []
