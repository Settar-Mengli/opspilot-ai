"""Rule-based triage adapter wrapping the existing keyword classifier."""

from opspilot.adapters.base import TriageAdapter
from opspilot.models.schemas import TriageRecord, WorkItem
from opspilot.rules.triage_rules import classify_work_item


class RuleBasedAdapter(TriageAdapter):
    """Adapter that delegates to the deterministic token-matching classifier."""

    def classify(self, item: WorkItem) -> TriageRecord:
        return classify_work_item(item)
