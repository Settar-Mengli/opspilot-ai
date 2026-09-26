"""Shared filesystem paths for the API."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
API_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
HISTORY_RUNS_DIR = PROJECT_ROOT / "data" / "history" / "runs"
RAW_INPUT_DIR = PROJECT_ROOT / "data" / "raw"
RUN_TIMEOUT_SECONDS = 120
