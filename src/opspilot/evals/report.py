"""Eval result JSON writers (no secrets / no prompt bodies)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_eval_json(path: Path | str, payload: dict[str, Any]) -> Path:
    """Write eval result JSON. Accepts ``Path`` or ``str`` (D4 write-path fix)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
