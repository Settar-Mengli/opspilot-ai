"""Eval result JSON writers (no secrets / no prompt bodies)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_eval_json(path: Path | str, payload: dict[str, Any]) -> Path:
    """Write eval result JSON atomically (temp + replace). Accepts ``Path`` or ``str``."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return target
