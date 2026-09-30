"""F-09: service LLM failures log error_code + redacted message only."""

from __future__ import annotations

import logging

import pytest

from opspilot.services._llm import _log_llm_failure


def test_log_llm_failure_redacts_key_material(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        _log_llm_failure("ask", RuntimeError("provider failed with sk-ant-abcdefghijklmnop token=sekrit"))
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "error_code=RuntimeError" in joined
    assert "sk-ant-abcdefghijklmnop" not in joined
    assert "sekrit" not in joined
    assert "***" in joined
