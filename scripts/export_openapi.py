"""Export OpenAPI schema for frontend openapi-typescript generation."""

from __future__ import annotations

import json
from pathlib import Path

from opspilot.api.app import app

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUT.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
