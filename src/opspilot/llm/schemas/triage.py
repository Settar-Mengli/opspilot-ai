"""Triage structured-output schema."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Urgency = Literal["critical", "high", "medium", "low"]
Category = Literal["incident", "request", "admin", "follow_up", "other"]
Sentiment = Literal["negative", "neutral", "positive"]


class TriagePayload(BaseModel):
    urgency: Urgency
    urgency_reason: str = Field(min_length=1, max_length=400)
    category: Category
    category_reason: str = Field(min_length=1, max_length=400)
    sentiment: Sentiment
    sentiment_reason: str = Field(min_length=1, max_length=400)
