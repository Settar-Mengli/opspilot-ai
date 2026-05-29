"""
FastAPI application for OpsPilot AI.
Exposes endpoints for health, running the pipeline, and retrieving outputs.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
import subprocess

API_OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..', 'data/output'))
RAW_INPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..', 'data/raw'))
PIPELINE_CLI = os.path.abspath(os.path.join(os.path.dirname(__file__), '../cli.py'))

app = FastAPI(title="OpsPilot AI API", description="Local API for running and retrieving OpsPilot outputs.", version="0.1.0")

class RunPipelineRequest(BaseModel):
    input_file: Optional[str] = 'sample_input.json'
    date: Optional[str] = None  # YYYY-MM-DD

@app.get("/health", response_class=PlainTextResponse)
def health():
    """Health check endpoint."""
    return "ok"

@app.post("/run")
def run_pipeline(req: RunPipelineRequest):
    """Run the OpsPilot pipeline with the given input file and date."""
    input_path = os.path.join(RAW_INPUT_DIR, req.input_file)
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail=f"Input file not found: {req.input_file}")
    output_dir = API_OUTPUT_DIR
    date_arg = req.date or ''
    cmd = [
        'python', PIPELINE_CLI, 'run',
        '--input', input_path,
        '--output', output_dir
    ]
    if date_arg:
        cmd += ['--date', date_arg]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"status": "success", "stdout": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e.stderr}")

@app.get("/briefing", response_class=PlainTextResponse)
def get_briefing():
    """Return the latest daily briefing text."""
    path = os.path.join(API_OUTPUT_DIR, 'daily_briefing.txt')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Briefing not found.")
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

@app.get("/triage", response_class=JSONResponse)
def get_triage():
    """Return the latest triage results as JSON."""
    path = os.path.join(API_OUTPUT_DIR, 'triage_results.json')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Triage results not found.")
    with open(path, 'r', encoding='utf-8') as f:
        return JSONResponse(content=f.read())
