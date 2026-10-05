"""Import boundary: morning_run must not import execute_pipeline or triage_connected_gmail."""

from __future__ import annotations

import ast
from pathlib import Path


def _collect_imports(source: str) -> set[str]:
    """Return all imported names/modules from Python source."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.add(module)
            for alias in node.names:
                names.add(alias.name)
                names.add(f"{module}.{alias.name}")
    return names


def test_no_execute_pipeline_import() -> None:
    """morning_run.py must not import execute_pipeline."""
    src = Path("src/opspilot/jobs/morning_run.py").read_text(encoding="utf-8")
    imports = _collect_imports(src)
    assert "execute_pipeline" not in imports, "morning_run imports execute_pipeline"
    assert not any("execute_pipeline" in n for n in imports), "morning_run imports execute_pipeline"


def test_no_triage_connected_gmail_import() -> None:
    """morning_run.py must not import triage_connected_gmail."""
    src = Path("src/opspilot/jobs/morning_run.py").read_text(encoding="utf-8")
    imports = _collect_imports(src)
    forbidden = {"triage_connected_gmail", "triage_connected_gmail_background"}
    found = imports & forbidden
    assert not found, f"morning_run imports forbidden names: {found}"
    # Also check string-level (catches dynamic imports).
    assert "triage_connected_gmail" not in src, "morning_run references triage_connected_gmail"
