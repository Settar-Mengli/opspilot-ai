"""FastAPI application — /api/v1 only."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from opspilot.api.errors import register_exception_handlers
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
    return application


app = create_app()
