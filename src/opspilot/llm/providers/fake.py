"""Deterministic fake provider for hermetic tests."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from pydantic import BaseModel

from opspilot.llm.types import AttemptStatus, Message, ProviderResult, StreamChunk, TaskName

JsonResponder = Callable[[TaskName, list[Message], type[BaseModel], str | None], str]
TextResponder = Callable[[TaskName, list[Message]], str]


@dataclass
class FakeProvider:
    """In-memory provider with optional scripted responses."""

    name: str = "fake"
    model: str = "fake-v1"
    text_responder: TextResponder | None = None
    json_responder: JsonResponder | None = None
    complete_results: list[ProviderResult] = field(default_factory=list)
    json_results: list[ProviderResult] = field(default_factory=list)
    stream_chunks: list[str] = field(default_factory=list)
    _complete_i: int = field(default=0, init=False, repr=False)
    _json_i: int = field(default=0, init=False, repr=False)

    def complete(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None = None,
    ) -> ProviderResult:
        started = time.perf_counter()
        if self.complete_results:
            result = self.complete_results[min(self._complete_i, len(self.complete_results) - 1)]
            self._complete_i += 1
            return result
        text = (
            self.text_responder(task, messages) if self.text_responder else f"fake:{task}:{messages[-1].content[:80]}"
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ProviderResult(
            status=AttemptStatus.SUCCESS,
            text=text[:max_tokens] if max_tokens > 0 else text,
            model=model or self.model,
            input_tokens=sum(len(m.content.split()) for m in messages),
            output_tokens=len(text.split()),
            latency_ms=latency_ms,
        )

    def complete_json(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        schema: type[BaseModel],
        max_tokens: int,
        model: str | None = None,
        repair_hint: str | None = None,
        force_json_object: bool = False,
    ) -> ProviderResult:
        del force_json_object  # fake ignores format mode
        started = time.perf_counter()
        if self.json_results:
            result = self.json_results[min(self._json_i, len(self.json_results) - 1)]
            self._json_i += 1
            return result
        if self.json_responder:
            text = self.json_responder(task, messages, schema, repair_hint)
        else:
            text = "{}"
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ProviderResult(
            status=AttemptStatus.SUCCESS,
            text=text[:max_tokens] if max_tokens > 0 else text,
            model=model or self.model,
            input_tokens=sum(len(m.content.split()) for m in messages),
            output_tokens=len(text.split()),
            latency_ms=latency_ms,
        )

    def stream(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None = None,
    ) -> Iterator[StreamChunk]:
        del messages  # fake ignores message body for scripted streams
        resolved = model or self.model
        chunks = self.stream_chunks or list(f"fake:{task}")
        emitted = 0
        for i, piece in enumerate(chunks):
            if max_tokens > 0 and emitted >= max_tokens:
                break
            text = piece[: max(0, max_tokens - emitted)] if max_tokens > 0 else piece
            emitted += len(text)
            yield StreamChunk(text=text, provider=self.name, model=resolved, done=i == len(chunks) - 1)
        if not chunks:
            yield StreamChunk(text="", provider=self.name, model=resolved, done=True)
