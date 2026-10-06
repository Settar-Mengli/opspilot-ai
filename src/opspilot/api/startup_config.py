"""Non-secret API startup config snapshot (STOP LIVE / ops)."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from opspilot.llm.policy import force_rules_enabled, llm_disable_enabled
from opspilot.llm.providers.anthropic import anthropic_enabled
from opspilot.persistence.repositories.anthropic_budget import get_budget
from opspilot.services.operator_session import demo_mode_enabled
from opspilot.services.send_allowlist import send_recipient_allowlist
from opspilot.utils.logging_utils import configure_logging


def anthropic_ledger_present() -> bool:
    """True when anthropic_prepaid_budget id=1 exists. Best-effort; False on DB errors."""
    try:
        from opspilot.persistence.db import create_engine, create_session_factory

        engine = create_engine()
        try:
            factory = create_session_factory(engine)
            with factory() as session:
                return get_budget(session) is not None
        finally:
            engine.dispose()
    except Exception:  # noqa: BLE001
        return False


def refuse_if_anthropic_enabled_with_demo() -> None:
    """Refuse process start when prepaid Anthropic is enabled under DEMO_MODE."""
    if anthropic_enabled() and demo_mode_enabled():
        raise RuntimeError("Refusing start: OPSPILOT_ANTHROPIC_ENABLED and OPSPILOT_DEMO_MODE cannot both be set")


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


def _env_flag(name: str) -> int:
    return int(os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"})


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _cors_first_origin_host_label() -> str:
    raw = os.environ.get("OPSPILOT_CORS_ORIGINS", "http://127.0.0.1:5173").strip()
    first = (raw.split(",")[0] if raw else "").strip() or "http://127.0.0.1:5173"
    host = urlparse(first).hostname or ""
    if not host:
        return "(none)"
    return host.split(".", 1)[0]


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
        f"ANTHROPIC_ENABLED={int(anthropic_enabled())} "
        f"ANTHROPIC_LEDGER={int(anthropic_ledger_present())} "
        f"CSRF_RELAX={_env_flag('OPSPILOT_CSRF_RELAX_DEV')} "
        f"COOKIE_SECURE={_env_flag('OPSPILOT_COOKIE_SECURE')} "
        f"CORS_ORIGIN_HOST={_cors_first_origin_host_label()} "
        f"ASK_MAX_STEPS={_env_int('OPSPILOT_ASK_MAX_STEPS', 5)} "
        f"ASK_MAX_PROVIDER_CALLS={_env_int('OPSPILOT_ASK_MAX_PROVIDER_CALLS', 8)}"
    )
    log.info("%s", line)
    return line
