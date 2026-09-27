"""Deprecated entrypoint — use ``opspilot.api.app:app`` instead.

Kept for one release as a compatibility shim. New docs and scripts must
target ``opspilot.api.app:app``.
"""

from __future__ import annotations

import warnings

from opspilot.api.app import app
from opspilot.api.paths import PROJECT_ROOT, RAW_INPUT_DIR

warnings.warn(
    "opspilot.api.main is deprecated; use opspilot.api.app:app",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "app",
    "PROJECT_ROOT",
    "RAW_INPUT_DIR",
]
