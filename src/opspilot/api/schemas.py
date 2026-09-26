"""Shared API request/response models and helpers."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel, Field

from opspilot.api.paths import RAW_INPUT_DIR

SAFE_RUN_METADATA_KEYS = {
    "run_id",
    "started_at",
    "finished_at",
    "duration_ms",
    "status",
    "item_count",
    "triage_count",
    "action_count",
    "suggested_response_count",
    "artifacts",
    "error",
}
SAFE_ARTIFACT_KEYS = {
    "triage_results",
    "action_items",
    "suggested_responses",
    "daily_briefing",
}
SAFE_ARTIFACT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class RunPipelineRequest(BaseModel):
    input_file: str = "sample_input.json"
    date: date


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    assistant_name: str = Field(
        default="OpsPilot",
        min_length=1,
        max_length=60,
        pattern=r"^[A-Za-z0-9 .'\-]+$",
    )


class EveningSummaryRequest(BaseModel):
    assistant_name: str = Field(
        default="OpsPilot",
        min_length=1,
        max_length=60,
        pattern=r"^[A-Za-z0-9 .'\-]+$",
    )


class InsightsRequest(BaseModel):
    assistant_name: str = Field(
        default="OpsPilot",
        min_length=1,
        max_length=60,
        pattern=r"^[A-Za-z0-9 .'\-]+$",
    )


def safe_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": code, "message": message},
    )


def safe_artifact_name(raw_name: object) -> str | None:
    if not isinstance(raw_name, str):
        return None
    candidate = raw_name.strip()
    if not candidate:
        return None
    if "/" in candidate or "\\" in candidate or ":" in candidate or ".." in candidate:
        return None
    if not SAFE_ARTIFACT_NAME.fullmatch(candidate):
        return None
    return candidate


def safe_history_metadata(payload: dict) -> dict:
    safe_payload: dict = {}
    for key in SAFE_RUN_METADATA_KEYS:
        if key == "artifacts":
            continue
        if key in payload:
            safe_payload[key] = payload[key]

    artifacts = payload.get("artifacts")
    if isinstance(artifacts, dict):
        safe_artifacts: dict[str, str] = {}
        for key, value in artifacts.items():
            if key not in SAFE_ARTIFACT_KEYS:
                continue
            name = safe_artifact_name(value)
            if name is not None:
                safe_artifacts[key] = name
        safe_payload["artifacts"] = safe_artifacts
    return safe_payload


def resolve_input_file(input_file: str) -> Path:
    candidate = Path(input_file)
    if (
        candidate.is_absolute()
        or any(part in {".", ".."} for part in candidate.parts)
        or len(candidate.parts) != 1
    ):
        raise HTTPException(status_code=400, detail="input_file must be a filename in data/raw")
    return RAW_INPUT_DIR / candidate.name
