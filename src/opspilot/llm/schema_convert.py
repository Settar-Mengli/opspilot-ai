"""Convert pydantic JSON Schema for provider structured-output APIs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel

# Keywords Gemini responseSchema rejects (INVALID_ARGUMENT on $defs/$ref and others).
_GEMINI_DROP = frozenset(
    {
        "$schema",
        "$id",
        "$defs",
        "definitions",
        "additionalProperties",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
        "if",
        "then",
        "else",
        "dependentSchemas",
        "dependentRequired",
        "unevaluatedItems",
        "unevaluatedProperties",
        "minContains",
        "maxContains",
        "prefixItems",
        "default",
        "examples",
        "title",
        "description",
    }
)


def _resolve_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            ref = str(node["$ref"])
            name = ref.rsplit("/", 1)[-1]
            if name not in defs:
                raise ValueError(f"unresolved $ref: {ref}")
            return _resolve_refs(deepcopy(defs[name]), defs)
        return {k: _resolve_refs(v, defs) for k, v in node.items() if k != "$defs"}
    if isinstance(node, list):
        return [_resolve_refs(v, defs) for v in node]
    return node


def _strip_gemini(node: Any) -> Any:
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for k, v in node.items():
            if k in _GEMINI_DROP:
                continue
            out[k] = _strip_gemini(v)
        return out
    if isinstance(node, list):
        return [_strip_gemini(v) for v in node]
    return node


def gemini_response_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """Inline $ref/$defs and drop keywords Gemini responseSchema rejects.

    Gemini generateContent generationConfig.responseSchema expects a subset of
    OpenAPI 3.0 Schema (no $ref/$defs). See Google AI Gemini API structured
    output docs for responseSchema / responseMimeType.
    """
    raw = schema.model_json_schema()
    defs = raw.get("$defs") or raw.get("definitions") or {}
    inlined = _resolve_refs(raw, defs)
    cleaned = _strip_gemini(inlined)
    if not isinstance(cleaned, dict):
        return {"type": "object"}
    cleaned.pop("$defs", None)
    cleaned.pop("definitions", None)
    return cleaned


def _force_additional_properties_false(node: Any) -> Any:
    if isinstance(node, dict):
        out = {k: _force_additional_properties_false(v) for k, v in node.items()}
        if out.get("type") == "object" or "properties" in out:
            out["additionalProperties"] = False
            props = out.get("properties") or {}
            if isinstance(props, dict) and props:
                out["required"] = sorted(props.keys())
        return out
    if isinstance(node, list):
        return [_force_additional_properties_false(v) for v in node]
    return node


def groq_strict_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """Strict-mode JSON Schema for Groq structured outputs (gpt-oss*).

    Groq requires additionalProperties:false on every object and required lists
    covering all properties (structured outputs docs).
    """
    out = _force_additional_properties_false(deepcopy(schema.model_json_schema()))
    if not isinstance(out, dict):
        return {"type": "object", "additionalProperties": False}
    if "$defs" in out and isinstance(out["$defs"], dict):
        out["$defs"] = {k: _force_additional_properties_false(v) for k, v in out["$defs"].items()}
    return out


def schema_prompt_fragment(schema: type[BaseModel]) -> str:
    """Compact schema reminder for json_object / prompt-only modes."""
    return f"Respond with a single JSON object matching this schema (field names exact): {schema.model_json_schema()}"
