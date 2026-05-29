from opspilot.models.schemas import ActionItem, TriageRecord, WorkItem


def draft_suggested_response(item: WorkItem, triage: TriageRecord, actions: list[ActionItem]) -> str:
    opening = _opening_for_category(triage.category)
    urgency_line = _urgency_line(triage.urgency)

    if actions:
        action = actions[0]
        action_line = "We will proceed on the requested action"
        if action.owner:
            action_line += f" with owner {action.owner}"
        if action.deadline:
            action_line += f" and target deadline {action.deadline}"
        action_line += "."
    else:
        action_line = "We will review and respond with the next step shortly."

    return f"{opening} {urgency_line} {action_line}".strip()


def _opening_for_category(category: str) -> str:
    if category == "incident":
        return "Thanks for flagging this incident."
    if category == "request":
        return "Thanks for your request."
    if category == "admin":
        return "Thanks for the administrative update."
    if category == "follow_up":
        return "Thanks for the follow up."
    return "Thanks for the update."


def _urgency_line(urgency: str) -> str:
    if urgency == "critical":
        return "This is marked as critical and is being handled immediately."
    if urgency == "high":
        return "This is marked as high priority and is being addressed now."
    if urgency == "medium":
        return "This is marked as medium priority and is queued for near-term action."
    return "This is marked as low priority and will be scheduled accordingly."
