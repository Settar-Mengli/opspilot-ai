"""Provider protocol for the hand-rolled LLM gateway."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from pydantic import BaseModel

from opspilot.llm.types import Message, ProviderResult, StreamChunk, TaskName


class LlmProvider(Protocol):
    """Minimal provider surface used by the gateway."""

    @property
    def name(self) -> str:
        """Stable provider id (gemini, groq, fake, …)."""

    def complete(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None = None,
    ) -> ProviderResult:
        """Prose completion attempt."""

    def complete_json(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        schema: type[BaseModel],
        max_tokens: int,
        model: str | None = None,
        repair_hint: str | None = None,
    ) -> ProviderResult:
        """Structured JSON completion attempt (schema enforced by gateway)."""

    def stream(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None = None,
    ) -> Iterator[StreamChunk]:
        """Prose token stream (no HTTP route until B5)."""
