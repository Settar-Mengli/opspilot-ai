"""Print the active database host first-label (never the full URL).

Usage (from repo root)::

    uv run python -m opspilot.jobs.db_host
"""

from __future__ import annotations

from opspilot.config.env_load import load_repo_dotenv
from opspilot.persistence.db import database_host_label


def main() -> int:
    load_repo_dotenv()
    print(f"database host={database_host_label()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
