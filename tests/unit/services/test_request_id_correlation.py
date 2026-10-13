"""LLM helpers resolve request_id from obs.request_context without importing the web app."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from opspilot.obs.request_context import request_id_ctx
from opspilot.services import _llm as llm_svc


def test_resolve_request_id_from_context_without_api_app() -> None:
    sys.modules.pop("opspilot.api.app", None)
    token = request_id_ctx.set("corr-req-42")
    try:
        assert llm_svc._resolve_request_id(None) == "corr-req-42"
        assert llm_svc._resolve_request_id("explicit") == "explicit"
        assert "opspilot.api.app" not in sys.modules
    finally:
        request_id_ctx.reset(token)


def test_api_app_reexports_request_id_ctx_from_obs() -> None:
    """app.py must import the shared ContextVar (single object at runtime)."""
    src = Path("src/opspilot/api/app.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "opspilot.obs.request_context":
            if any(alias.name == "request_id_ctx" for alias in node.names):
                found = True
                break
    assert found, "api.app must import request_id_ctx from opspilot.obs.request_context"
