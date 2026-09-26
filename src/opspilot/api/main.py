"""Backward-compatible entry: prefer `opspilot.api.app:app`."""

from opspilot.api.app import app
from opspilot.api.paths import API_OUTPUT_DIR, HISTORY_RUNS_DIR, PROJECT_ROOT, RAW_INPUT_DIR

__all__ = [
    "app",
    "API_OUTPUT_DIR",
    "HISTORY_RUNS_DIR",
    "PROJECT_ROOT",
    "RAW_INPUT_DIR",
]
