"""
FastAPI application for OpsPilot AI.
Exposes endpoints for health, running the pipeline, and retrieving outputs.
"""
import json
import logging
import re
import sys
from datetime import date
from pathlib import Path

from opspilot.adapters.conversation_adapter import answer_question
from opspilot.adapters.evening_adapter import generate_evening_summary
from opspilot.adapters.insights_adapter import generate_insights
from opspilot.history.run_history import (
    list_run_metadata,
    read_run_json_artifact,
    read_run_metadata,
    read_run_text_artifact,
)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[3]
API_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
HISTORY_RUNS_DIR = PROJECT_ROOT / "data" / "history" / "runs"
RAW_INPUT_DIR = PROJECT_ROOT / "data" / "raw"
RUN_TIMEOUT_SECONDS = 120
LOCAL_UI_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
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

logger = logging.getLogger("opspilot.api")

app = FastAPI(title="OpsPilot AI API", description="Local API for running and retrieving OpsPilot outputs.", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_UI_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class RunPipelineRequest(BaseModel):
    input_file: str = "sample_input.json"
    date: date


class AskRequest(BaseModel):
    question: str
    assistant_name: str = "OpsPilot"


class EveningSummaryRequest(BaseModel):
    assistant_name: str = "OpsPilot"


class InsightsRequest(BaseModel):
    assistant_name: str = "OpsPilot"


def _safe_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": code, "message": message},
    )


def _safe_artifact_name(raw_name: object) -> str | None:
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


def _safe_history_metadata(payload: dict) -> dict:
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
            safe_name = _safe_artifact_name(value)
            if safe_name is not None:
                safe_artifacts[key] = safe_name
        safe_payload["artifacts"] = safe_artifacts

    return safe_payload


def _resolve_input_file(input_file: str) -> Path:
    """Allow only simple filenames from data/raw to prevent path traversal."""
    candidate = Path(input_file)
    if candidate.is_absolute() or any(part in {".", ".."} for part in candidate.parts) or len(candidate.parts) != 1:
        raise HTTPException(status_code=400, detail="input_file must be a filename in data/raw")
    return RAW_INPUT_DIR / candidate.name

@app.get("/health", response_class=PlainTextResponse)
def health():
    """Health check endpoint."""
    return "ok"

@app.post("/run")
def run_pipeline(req: RunPipelineRequest):
    """Run the OpsPilot pipeline with the given input file and date."""
    input_path = _resolve_input_file(req.input_file)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail=f"Input file not found: {req.input_file}")

    cmd = [
        sys.executable,
        "-m",
        "opspilot.cli",
        "run",
        "--input",
        str(input_path),
        "--output",
        str(API_OUTPUT_DIR),
        "--date",
        req.date.isoformat(),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
        return {"status": "success", "stdout": result.stdout}
    except subprocess.TimeoutExpired as exc:
        logger.error(
            "pipeline_run_timeout",
            extra={"timeout_seconds": RUN_TIMEOUT_SECONDS, "cmd": cmd, "error": str(exc)},
        )
        raise _safe_error(504, "pipeline_timeout", "Pipeline run timed out.")
    except subprocess.CalledProcessError as e:
        logger.error(
            "pipeline_run_failed",
            extra={"cmd": cmd, "returncode": e.returncode, "stderr": (e.stderr or "")[:1000]},
        )
        raise _safe_error(500, "pipeline_failed", "Pipeline execution failed.")

@app.get("/briefing", response_class=PlainTextResponse)
def get_briefing():
    """Return the latest daily briefing text."""
    path = API_OUTPUT_DIR / "daily_briefing.txt"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Briefing not found.")
    with path.open("r", encoding="utf-8") as f:
        return f.read()


@app.get("/runs", response_class=JSONResponse)
def get_runs():
    """Return metadata for all local history runs, newest first."""
    metadata = list_run_metadata(HISTORY_RUNS_DIR)
    return [_safe_history_metadata(item) for item in metadata]


@app.get("/runs/{run_id}", response_class=JSONResponse)
def get_run(run_id: str):
    """Return metadata for a specific run."""
    try:
        metadata = read_run_metadata(run_id, HISTORY_RUNS_DIR)
    except (OSError, ValueError):
        raise _safe_error(500, "run_read_failed", "Failed to read run metadata.")

    if metadata is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    return _safe_history_metadata(metadata)

@app.get("/triage", response_class=JSONResponse)
def get_triage():
    """Return the latest triage results as JSON."""
    path = API_OUTPUT_DIR / "triage_results.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Triage results not found.")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/runs/{run_id}/triage", response_class=JSONResponse)
def get_run_triage(run_id: str):
    """Return triage results for a specific run."""
    try:
        payload = read_run_json_artifact(run_id, "triage_results.json", HISTORY_RUNS_DIR)
    except FileNotFoundError:
        raise _safe_error(404, "artifact_not_found", "Run triage artifact not found.")
    except (OSError, ValueError):
        raise _safe_error(500, "artifact_read_failed", "Failed to read run triage artifact.")

    if payload is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    return payload


@app.get("/runs/{run_id}/briefing", response_class=PlainTextResponse)
def get_run_briefing(run_id: str):
    """Return briefing text for a specific run."""
    try:
        payload = read_run_text_artifact(run_id, "daily_briefing.txt", HISTORY_RUNS_DIR)
    except FileNotFoundError:
        raise _safe_error(404, "artifact_not_found", "Run briefing artifact not found.")
    except (OSError, ValueError):
        raise _safe_error(500, "artifact_read_failed", "Failed to read run briefing artifact.")

    if payload is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    return payload


@app.get("/ai-briefing", response_class=PlainTextResponse)
def get_ai_briefing():
    """Return the latest AI-generated executive briefing."""
    ai_path = API_OUTPUT_DIR / "ai_briefing.txt"
    if ai_path.exists():
        with ai_path.open("r", encoding="utf-8") as f:
            return f.read()
    # Fallback to daily_briefing.txt
    fallback_path = API_OUTPUT_DIR / "daily_briefing.txt"
    if not fallback_path.exists():
        raise HTTPException(status_code=404, detail="No briefing available.")
    with fallback_path.open("r", encoding="utf-8") as f:
        return f.read()


@app.get("/runs/{run_id}/ai-briefing", response_class=PlainTextResponse)
def get_run_ai_briefing(run_id: str):
    """Return AI briefing text for a specific run."""
    try:
        payload = read_run_text_artifact(run_id, "ai_briefing.txt", HISTORY_RUNS_DIR)
    except FileNotFoundError:
        # Fall back to daily_briefing.txt for this run
        try:
            payload = read_run_text_artifact(run_id, "daily_briefing.txt", HISTORY_RUNS_DIR)
        except (FileNotFoundError, OSError, ValueError):
            raise _safe_error(404, "artifact_not_found", "Run AI briefing artifact not found.")
    except (OSError, ValueError):
        raise _safe_error(500, "artifact_read_failed", "Failed to read run AI briefing artifact.")

    if payload is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    return payload


@app.post("/ask")
def ask(payload: AskRequest) -> dict[str, str]:
    """Answer a free-form question with triage context."""
    # Load current triage records to give the assistant context
    triage_path = API_OUTPUT_DIR / "triage_results.json"
    records: list = []
    if triage_path.exists():
        try:
            with triage_path.open("r", encoding="utf-8") as f:
                records = json.load(f)
        except (OSError, json.JSONDecodeError):
            records = []

    answer = answer_question(
        question=payload.question,
        assistant_name=payload.assistant_name,
        triage_records=records,
    )
    return {"answer": answer}


@app.post("/evening-summary")
def evening_summary(payload: EveningSummaryRequest) -> dict[str, str]:
    """Generate an end-of-day summary based on today's triage records."""
    triage_path = API_OUTPUT_DIR / "triage_results.json"
    records: list = []
    if triage_path.exists():
        try:
            with triage_path.open("r", encoding="utf-8") as f:
                records = json.load(f)
        except (OSError, json.JSONDecodeError):
            records = []

    summary = generate_evening_summary(
        assistant_name=payload.assistant_name,
        triage_records=records,
    )
    return {"summary": summary}


@app.post("/insights")
def insights(payload: InsightsRequest) -> dict[str, object]:
    """Generate cross-cutting insights based on current triage records."""
    triage_path = API_OUTPUT_DIR / "triage_results.json"
    records: list = []
    if triage_path.exists():
        try:
            with triage_path.open("r", encoding="utf-8") as f:
                records = json.load(f)
        except (OSError, json.JSONDecodeError):
            records = []

    result = generate_insights(
        assistant_name=payload.assistant_name,
        triage_records=records,
    )
    return result


@app.get("/inputs", response_class=JSONResponse)
def get_inputs():
    """Return list of .json input files in data/raw/."""
    if not RAW_INPUT_DIR.exists():
        return {"files": []}
    files = sorted(f.name for f in RAW_INPUT_DIR.iterdir() if f.is_file() and f.suffix == ".json")
    return {"files": files}
