"""
FastAPI application for OpsPilot AI.
Exposes endpoints for health, running the pipeline, and retrieving outputs.
"""
import json
import logging
import sys
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[3]
API_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
RAW_INPUT_DIR = PROJECT_ROOT / "data" / "raw"
RUN_TIMEOUT_SECONDS = 30

logger = logging.getLogger("opspilot.api")

app = FastAPI(title="OpsPilot AI API", description="Local API for running and retrieving OpsPilot outputs.", version="0.1.0")

class RunPipelineRequest(BaseModel):
    input_file: str = "sample_input.json"
    date: date


def _safe_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": code, "message": message},
    )


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

@app.get("/triage", response_class=JSONResponse)
def get_triage():
    """Return the latest triage results as JSON."""
    path = API_OUTPUT_DIR / "triage_results.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Triage results not found.")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
