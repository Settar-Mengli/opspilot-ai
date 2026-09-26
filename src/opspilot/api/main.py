"""Backward-compatible entry: prefer `opspilot.api.app:app`."""

from opspilot.api.app import app
from opspilot.api.paths import PROJECT_ROOT, RAW_INPUT_DIR

__all__ = [
    "app",
    "PROJECT_ROOT",
    "RAW_INPUT_DIR",
]
