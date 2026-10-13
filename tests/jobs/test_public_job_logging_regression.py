"""Regression: job LLM path must not boot api.app or leak INFO httpx / free-text spans."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

_SCRIPT = r"""
import logging
import os
import sys

# Pin public CI env (subprocess inherits explicitly).
os.environ["CI"] = "true"
os.environ["GITHUB_ACTIONS"] = "true"
os.environ["OPSPILOT_LLM_JSONL"] = "1"
os.environ.pop("OPSPILOT_FORCE_RULES", None)
os.environ.pop("OPSPILOT_LLM_DISABLE", None)

from opspilot.jobs.logging_setup import configure_public_job_logging

configure_public_job_logging()

root = logging.getLogger()
level_after_setup = root.level
handlers_after_setup = list(root.handlers)

from opspilot.obs.tracing import LlmSpanAttrs, append_llm_jsonl, emit_llm_span
from opspilot.services import _llm as llm_svc

assert "opspilot.api.app" not in sys.modules

# Span with free-text meta must strip under GITHUB_ACTIONS (logged at INFO on tracing logger).
emit_llm_span(
    LlmSpanAttrs(
        task="ask",
        provider="fake",
        model="m",
        status="error",
        meta={
            "status_code": 500,
            "provider_error": "SECRET_PROVIDER_BODY",
            "output_head": "SECRET_OUTPUT_HEAD",
            "validation_error": "SECRET_VALIDATION",
            "error_class": "ValueError",
            "output_len": 3,
        },
    )
)
assert append_llm_jsonl(
    LlmSpanAttrs(task="ask", provider="fake", model="m", status="success")
) is None

# Resolve request id without importing the web app.
assert llm_svc._resolve_request_id(None) is None
assert "opspilot.api.app" not in sys.modules

# Root must not have been promoted to API INFO by a create_app side effect.
assert root.level == level_after_setup == logging.WARNING
assert root.handlers == handlers_after_setup
assert logging.getLogger("httpx").level >= logging.WARNING

print("REGRESSION_OK")
"""


def test_job_llm_path_no_api_app_no_http_request_leak() -> None:
    env = {
        **os.environ,
        "CI": "true",
        "GITHUB_ACTIONS": "true",
        "DATABASE_URL": "postgresql+psycopg://opspilot:opspilot@127.0.0.1:5432/opspilot",
    }
    # Avoid loading Neon from a parent shell; do not pass secrets.
    proc = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        cwd=str(_REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "REGRESSION_OK" in out
    assert "HTTP Request:" not in out
    assert "SECRET_PROVIDER_BODY" not in out
    assert "SECRET_OUTPUT_HEAD" not in out
    assert "SECRET_VALIDATION" not in out
    assert "startup_config" not in out
