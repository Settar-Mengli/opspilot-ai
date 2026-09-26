"""FastAPI application factory — /api/v1 + legacy aliases."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from opspilot.api.errors import register_exception_handlers
from opspilot.api.v1.routes import (
    ask,
    create_run,
    evening_summary,
    get_ai_briefing,
    get_briefing,
    get_capability_by_id,
    get_inputs,
    get_run,
    get_run_ai_briefing,
    get_run_briefing,
    get_run_triage,
    get_settings,
    get_triage,
    health,
    insights,
    list_capabilities,
    list_runs,
)
from opspilot.api.v1.routes import router as v1_router

LOCAL_UI_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app() -> FastAPI:
    application = FastAPI(
        title="OpsPilot AI API",
        description="Local API for running and retrieving OpsPilot outputs.",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=LOCAL_UI_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    register_exception_handlers(application)
    application.include_router(v1_router)

    # Legacy thin aliases (removed in commit 9 with FE cutover).
    application.add_api_route("/health", health, methods=["GET"], response_class=PlainTextResponse)
    application.add_api_route("/run", create_run, methods=["POST"])
    application.add_api_route(
        "/briefing", get_briefing, methods=["GET"], response_class=PlainTextResponse
    )
    application.add_api_route("/triage", get_triage, methods=["GET"])
    application.add_api_route("/runs", list_runs, methods=["GET"])
    application.add_api_route("/runs/{run_id}", get_run, methods=["GET"])
    application.add_api_route("/runs/{run_id}/triage", get_run_triage, methods=["GET"])
    application.add_api_route(
        "/runs/{run_id}/briefing",
        get_run_briefing,
        methods=["GET"],
        response_class=PlainTextResponse,
    )
    application.add_api_route(
        "/ai-briefing", get_ai_briefing, methods=["GET"], response_class=PlainTextResponse
    )
    application.add_api_route(
        "/runs/{run_id}/ai-briefing",
        get_run_ai_briefing,
        methods=["GET"],
        response_class=PlainTextResponse,
    )
    application.add_api_route("/ask", ask, methods=["POST"])
    application.add_api_route("/evening-summary", evening_summary, methods=["POST"])
    application.add_api_route("/insights", insights, methods=["POST"])
    application.add_api_route("/inputs", get_inputs, methods=["GET"])
    application.add_api_route("/capabilities", list_capabilities, methods=["GET"])
    application.add_api_route(
        "/capabilities/{capability_id}", get_capability_by_id, methods=["GET"]
    )
    application.add_api_route("/api/settings", get_settings, methods=["GET"])
    # PATCH /api/settings intentionally removed (SEC-01 / AI-02).

    return application


app = create_app()
