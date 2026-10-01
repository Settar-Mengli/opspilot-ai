"""Eval dataset loaders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opspilot.models.schemas import WorkItem


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "evals" / "datasets").is_dir():
            return parent
    return here.parents[3]


REPO_ROOT = _repo_root()
TRIAGE_V1 = REPO_ROOT / "evals" / "datasets" / "triage" / "v1"
REDTEAM_V1 = REPO_ROOT / "evals" / "datasets" / "redteam" / "v1"
ASK_AGENT_V1 = REPO_ROOT / "evals" / "datasets" / "ask_agent" / "v1"
REDTEAM_AGENT_V1 = REPO_ROOT / "evals" / "datasets" / "redteam_agent" / "v1"


def load_jsonl_cases(target: Path) -> list[dict[str, Any]]:
    if not target.exists():
        return []
    cases: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        cases.append(json.loads(line))
    return cases


def load_triage_cases(path: Path | None = None) -> list[dict[str, Any]]:
    return load_jsonl_cases(path or (TRIAGE_V1 / "cases.jsonl"))


def case_to_work_item(case: dict[str, Any]) -> WorkItem:
    return WorkItem(
        id=str(case["id"]),
        source_type=str(case.get("source_type") or "email"),
        subject_or_title=str(case.get("subject_or_title") or ""),
        body_or_description=str(case.get("body_or_description") or ""),
        sender_or_requester=str(case.get("sender_or_requester") or ""),
        received_at=str(case.get("received_at") or ""),
        tags=list(case.get("tags") or []),
    )


def load_redteam_cases(path: Path | None = None) -> list[dict[str, Any]]:
    return load_jsonl_cases(path or (REDTEAM_V1 / "attacks.jsonl"))


def load_ask_agent_cases(path: Path | None = None) -> list[dict[str, Any]]:
    return load_jsonl_cases(path or (ASK_AGENT_V1 / "cases.jsonl"))


def load_redteam_agent_cases(path: Path | None = None) -> list[dict[str, Any]]:
    return load_jsonl_cases(path or (REDTEAM_AGENT_V1 / "attacks.jsonl"))
