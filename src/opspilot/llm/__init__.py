"""LLM gateway package (B2)."""

from opspilot.llm.errors import LlmError, LlmPolicyDenied, LlmProvidersExhausted, LlmSchemaError
from opspilot.llm.gateway import LlmGateway, complete, complete_json, session_attempt_recorder, stream
from opspilot.llm.policy import llm_allowed
from opspilot.llm.providers import FakeProvider
from opspilot.llm.types import AttemptStatus, CompletionResult, Message, StreamChunk

__all__ = [
    "AttemptStatus",
    "CompletionResult",
    "FakeProvider",
    "LlmError",
    "LlmGateway",
    "LlmPolicyDenied",
    "LlmProvidersExhausted",
    "LlmSchemaError",
    "Message",
    "StreamChunk",
    "complete",
    "complete_json",
    "llm_allowed",
    "session_attempt_recorder",
    "stream",
]
