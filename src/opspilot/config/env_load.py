"""Repo .env loading — same pattern as eval / pipeline / llm_discover CLIs."""

from __future__ import annotations

from dotenv import load_dotenv


def load_repo_dotenv() -> bool:
    """Load repo-root ``.env`` into ``os.environ`` without overriding existing keys.

    Matches ``load_dotenv()`` used by ``run_evals`` / ``run_daily_ops`` / ``llm_discover``.
    """
    return bool(load_dotenv())
