"""Insights schema for structured gateway output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class InsightItem(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1)
    category: str = Field(default="general", min_length=1, max_length=64)


class InsightsPayload(BaseModel):
    """Cross-cutting insights. Non-empty insights required when LLM is invoked on a non-empty queue."""

    intro: str = Field(min_length=1)
    insights: list[InsightItem] = Field(min_length=1)
