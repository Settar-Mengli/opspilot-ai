"""Provider-agnostic contract for triage classification adapters.

Any classification provider (rule-based, LLM-backed, etc.) must implement
the TriageAdapter interface to be usable by the pipeline orchestrator.
"""

from abc import ABC, abstractmethod

from opspilot.models.schemas import TriageRecord, WorkItem


class TriageAdapter(ABC):
    """Abstract base class defining the triage classification contract."""

    @abstractmethod
    def classify(self, item: WorkItem) -> TriageRecord:
        """Classify a work item and return a fully populated TriageRecord."""
