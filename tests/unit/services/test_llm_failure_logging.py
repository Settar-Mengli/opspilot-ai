"""F-09: service LLM failures log error_code + redacted message only."""

from __future__ import annotations

import pytest

from opspilot.services import _llm as llm_svc


def test_log_llm_failure_redacts_key_material(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[str] = []

    def _capture(msg: str, *args: object, **_kwargs: object) -> None:
        recorded.append(msg % args if args else msg)

    monkeypatch.setattr(llm_svc.logger, "error", _capture)
    llm_svc._log_llm_failure(
        "ask",
        RuntimeError("provider failed with sk-ant-abcdefghijklmnop token=sekrit"),
    )
    joined = "\n".join(recorded)
    assert "error_code=RuntimeError" in joined
    assert "sk-ant-abcdefghijklmnop" not in joined
    assert "sekrit" not in joined
    assert "***" in joined
