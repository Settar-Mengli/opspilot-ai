"""Public-job logging contract (morning_run / db_host)."""

from __future__ import annotations

import logging

from opspilot.utils.logging_utils import in_github_actions

__all__ = ["configure_public_job_logging", "in_github_actions"]


def configure_public_job_logging() -> None:
    """Root and noisy HTTP loggers at WARNING+ (no INFO URL lines in public CI)."""
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    if not root.handlers:
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    else:
        root.setLevel(logging.WARNING)
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
