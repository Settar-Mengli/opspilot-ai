"""Nothing under jobs/services/llm/obs/integrations may import opspilot.api.app."""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path("src/opspilot")
_PACKAGES = ("jobs", "services", "llm", "obs", "integrations")
_FORBIDDEN = "opspilot.api.app"


def _collect_import_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_jobs_services_llm_obs_integrations_do_not_import_api_app() -> None:
    violations: list[str] = []
    for pkg in _PACKAGES:
        base = _ROOT / pkg
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            src = path.read_text(encoding="utf-8")
            for mod in _collect_import_modules(src):
                if mod == _FORBIDDEN or mod.startswith(_FORBIDDEN + "."):
                    violations.append(f"{path.as_posix()}: imports {mod}")
            # Dynamic / string form used by the old _llm lazy import.
            if f"from {_FORBIDDEN} import" in src or f"import {_FORBIDDEN}" in src:
                line_hit = f"{path.as_posix()}: string reference to {_FORBIDDEN}"
                if line_hit not in violations:
                    violations.append(line_hit)
    assert not violations, "forbidden opspilot.api.app imports:\n" + "\n".join(violations)
