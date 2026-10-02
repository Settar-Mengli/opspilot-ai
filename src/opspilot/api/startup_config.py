"""Non-secret API startup config snapshot (STOP LIVE / ops)."""

from __future__ import annotations

import logging

from opspilot.llm.policy import force_rules_enabled, llm_disable_enabled
from opspilot.llm.providers.anthropic import anthropic_enabled
from opspilot.services.operator_session import demo_mode_enabled
from opspilot.services.send_allowlist import send_recipient_allowlist
from opspilot.utils.logging_utils import configure_logging


def ensure_api_logging() -> None:
    """Make opspilot.* INFO lines visible under uvicorn (root often WARNING-only)."""
    configure_logging(logging.INFO)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for name in (
        "opspilot",
        "opspilot.api",
        "opspilot.api.access",
        "opspilot.api.ask",
    ):
        logging.getLogger(name).setLevel(logging.INFO)


def log_startup_config(*, logger: logging.Logger | None = None) -> str:
    """Log effective non-secret flags; return the same one-line summary."""
    log = logger or logging.getLogger("opspilot.api")
    allow = send_recipient_allowlist()
    allow_n = 0 if allow is None else len(allow)
    line = (
        "startup_config "
        f"FORCE_RULES={int(force_rules_enabled())} "
        f"LLM_DISABLE={int(llm_disable_enabled())} "
        f"DEMO_MODE={int(demo_mode_enabled())} "
        f"allowlist_count={allow_n} "
        f"ANTHROPIC_ENABLED={int(anthropic_enabled())}"
    )
    log.info("%s", line)
    return line
