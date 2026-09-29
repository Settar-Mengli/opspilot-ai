"""Application services (B2)."""

from opspilot.services.ask import answer_question
from opspilot.services.evening import generate_evening_summary
from opspilot.services.insights import generate_insights

__all__ = ["answer_question", "generate_evening_summary", "generate_insights"]
