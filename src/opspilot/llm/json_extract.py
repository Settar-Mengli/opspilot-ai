"""Extract a JSON object from model text (fences / prose wrapping)."""

from __future__ import annotations


def extract_json_object(text: str) -> str:
    """Return the first balanced {...} substring, stripping markdown fences."""
    raw = (text or "").strip()
    if not raw:
        return ""
    if raw.startswith("```"):
        lines = raw.splitlines()
        # drop opening fence
        if lines:
            lines = lines[1:]
        # drop closing fence
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].lstrip()
    start = raw.find("{")
    if start < 0:
        return raw
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(raw)):
        ch = raw[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    return raw[start:]
