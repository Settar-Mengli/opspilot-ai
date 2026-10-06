"""Normalize Ask agent turns and validate per-tool args (D-031)."""

from __future__ import annotations

import json
from typing import Any

from opspilot.llm.json_extract import extract_json_object

_ARG_BAG_KEYS = ("args", "arguments", "parameters", "input")
_TOP_LEVEL_RESERVED = frozenset({"kind", "tool", "final", "args", "arguments", "parameters", "input"})


def collect_key_paths(value: Any, *, prefix: str = "") -> list[str]:
    """Return sorted KEY paths only (no values) for logging."""
    out: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value.keys(), key=lambda k: str(k)):
            path = f"{prefix}.{key}" if prefix else str(key)
            out.append(path)
            out.extend(collect_key_paths(value[key], prefix=path))
    elif isinstance(value, list):
        for i, item in enumerate(value[:20]):
            path = f"{prefix}[{i}]"
            out.extend(collect_key_paths(item, prefix=path))
    return out


def parse_raw_turn_dict(raw: str | dict[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    try:
        data = json.loads(extract_json_object(text))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def normalize_tool_args(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Extract tool args from common shapes; conflict → error code.

    Accepted bags: args | arguments | parameters | input (must be objects).
    Flat top-level keys other than kind/tool/final/bags are also accepted.
    If more than one non-empty source disagrees, return conflict error.
    """
    bags: list[tuple[str, dict[str, Any]]] = []
    for key in _ARG_BAG_KEYS:
        if key not in data:
            continue
        val = data[key]
        if val is None:
            continue
        if not isinstance(val, dict):
            return None, f"args_bag_not_object:{key}"
        bags.append((key, dict(val)))

    flat = {k: v for k, v in data.items() if k not in _TOP_LEVEL_RESERVED}
    candidates: list[tuple[str, dict[str, Any]]] = list(bags)
    if flat:
        candidates.append(("flat", flat))

    non_empty = [(name, blob) for name, blob in candidates if blob]
    if not non_empty:
        return {}, None

    # Identical content is fine even from multiple keys.
    canonical = json.dumps(non_empty[0][1], sort_keys=True, default=str)
    for name, blob in non_empty[1:]:
        if json.dumps(blob, sort_keys=True, default=str) != canonical:
            return None, f"args_conflict:{non_empty[0][0]}+{name}"
    return dict(non_empty[0][1]), None


def validate_tool_args(tool: str, args: dict[str, Any]) -> list[str]:
    """Return content-free schema error codes; empty list = ok."""
    errors: list[str] = []
    if tool == "draft_reply":
        item_id = str(args.get("work_item_id") or args.get("id") or "").strip()
        body = str(args.get("body") or "").strip()
        if not item_id:
            errors.append("missing_work_item_id")
        if not body:
            errors.append("missing_body")
        return errors
    if tool == "get_message":
        item_id = str(args.get("id") or args.get("work_item_id") or "").strip()
        if not item_id:
            errors.append("missing_id")
        return errors
    if tool == "search_items":
        if "limit" in args and args.get("limit") is not None:
            try:
                limit = int(args["limit"])
            except (TypeError, ValueError):
                errors.append("invalid_limit")
            else:
                if limit < 1 or limit > 20:
                    errors.append("limit_out_of_range")
        return errors
    if tool == "get_calendar":
        if "days" in args and args.get("days") is not None:
            try:
                days = int(args["days"])
            except (TypeError, ValueError):
                errors.append("invalid_days")
            else:
                if days < 1 or days > 14:
                    errors.append("days_out_of_range")
        return errors
    if tool == "get_me":
        return errors
    if tool == "get_file_contents":
        path = str(args.get("path") or "").strip()
        if not path:
            errors.append("missing_path")
        return errors
    if tool == "list_commits":
        if "limit" in args and args.get("limit") is not None:
            try:
                limit = int(args["limit"])
            except (TypeError, ValueError):
                errors.append("invalid_limit")
            else:
                if limit < 1 or limit > 20:
                    errors.append("limit_out_of_range")
        return errors
    if tool == "pull_request_read":
        raw = args.get("pull_number")
        if raw is None or str(raw).strip() == "":
            errors.append("missing_pull_number")
            return errors
        try:
            number = int(raw)
        except (TypeError, ValueError):
            errors.append("invalid_pull_number")
        else:
            if number <= 0:
                errors.append("invalid_pull_number")
        return errors
    errors.append("unknown_tool")
    return errors


def schema_repair_message(*, tool: str, errors: list[str]) -> str:
    """Trusted, content-free repair instruction for invalid tool args."""
    codes = ",".join(errors) if errors else "invalid_args"
    return (
        f"Tool args invalid for {tool}: {codes}. "
        "Respond with one JSON object using args (or arguments) matching the tool schema. "
        "draft_reply requires work_item_id (exact id from search_items) and body; "
        "subject is optional. Do not invent Gmail provider ids."
    )
