"""Convert pydantic JSON Schema for provider structured-output APIs."""

from __future__ import annotations

from collections.abc import Collection
from copy import deepcopy
from typing import Any, Literal, get_args, get_origin

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
            if k == "properties" and isinstance(v, dict):
                # Property *names* must be preserved (e.g. field "title"); only strip
                # metadata keywords on nested schema objects, never on the key map.
                out[k] = {pk: _strip_gemini(pv) for pk, pv in v.items()}
            else:
                out[k] = _strip_gemini(v)
        # Drop required entries that no longer exist after stripping.
        if "required" in out and "properties" in out and isinstance(out["properties"], dict):
            props = out["properties"]
            req = out.get("required")
            if isinstance(req, list):
                out["required"] = [r for r in req if r in props]
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


def instance_schema_prompt(
    schema: type[BaseModel],
    *,
    allowed_ids: Collection[str] | None = None,
) -> str:
    """Flat instance JSON contract for prompts (never dump model_json_schema meta).

    Same text shape for every provider path that appends a schema reminder
    (json_object, Groq strict reminder, Gemini force_json_object, repair).
    """
    required = [n for n, f in schema.model_fields.items() if f.is_required()]
    # Always call out confidence / evidence_refs when present even if not pydantic-required.
    for extra in ("confidence", "evidence_refs"):
        if extra in schema.model_fields and extra not in required:
            required.append(extra)
    lines = [
        "Respond with a single flat JSON object (instance values only — NOT a JSON Schema).",
        'Do not wrap fields under "properties", "description", "$defs", or "type".',
        f"Required keys (exact names): {required}.",
    ]
    for name, field in schema.model_fields.items():
        if name == "confidence":
            lines.append('- "confidence": number between 0 and 1 inclusive')
            continue
        if name == "evidence_refs":
            if allowed_ids:
                ids = list(allowed_ids)
                lines.append(
                    f'- "evidence_refs": non-empty JSON array of strings; '
                    f"every element must be one of the allowed ids {ids} (subset only)"
                )
            else:
                lines.append(
                    '- "evidence_refs": non-empty JSON array of strings; every element must equal '
                    'the id attribute on the <<<UNTRUSTED id="...">>> delimiter in the user message'
                )
            continue
        ann = field.annotation
        origin = get_origin(ann)
        args = get_args(ann)
        if origin is Literal:
            lit = list(args)
            if lit and all(isinstance(v, str) for v in lit):
                lines.append(f'- "{name}": one of {lit}')
                continue
        if origin is list:
            inner = args[0] if args else str
            if get_origin(inner) is Literal:
                lit = list(get_args(inner))
                lines.append(f'- "{name}": JSON array; each element one of {lit}')
            else:
                lines.append(f'- "{name}": JSON array of strings')
            continue
        if ann is float:
            lines.append(f'- "{name}": number')
            continue
        if ann is int:
            lines.append(f'- "{name}": integer')
            continue
        min_len = None
        for m in field.metadata:
            min_len = getattr(m, "min_length", min_len)
        if min_len:
            lines.append(f'- "{name}": non-empty string (min_length={min_len})')
        else:
            lines.append(f'- "{name}": string')
    return "\n".join(lines)


def schema_prompt_fragment(
    schema: type[BaseModel],
    *,
    allowed_ids: Collection[str] | None = None,
) -> str:
    """Prompt reminder for structured JSON (instance contract, not JSON Schema dump)."""
    return instance_schema_prompt(schema, allowed_ids=allowed_ids)


def unwrap_schema_echo(data: Any) -> Any:
    """Last-resort unwrap when a model echoes JSON-Schema shape with instance values under properties.

    Redacted Mistral failure shape::
        {"description": "...", "properties": {"urgency": "high", ...}}
    becomes the inner properties dict when top-level lacks the instance keys.
    """
    if not isinstance(data, dict):
        return data
    props = data.get("properties")
    if not isinstance(props, dict) or not props:
        return data
    # Real JSON Schema keeps {"type": ...} objects under properties; instance echoes use scalars/lists.
    schema_like = 0
    instance_like = 0
    for v in props.values():
        if isinstance(v, dict) and ("type" in v or "$ref" in v or "properties" in v):
            schema_like += 1
        else:
            instance_like += 1
    if instance_like == 0 or schema_like > instance_like:
        return data
    # Prefer unwrap when top-level looks like schema meta (description/type/$schema) or
    # lacks any of the property keys at the top level.
    meta_keys = {"description", "type", "$schema", "$defs", "title", "required", "additionalProperties"}
    top_meta = sum(1 for k in data if k in meta_keys)
    top_has_prop_key = any(k in data for k in props)
    if top_meta > 0 or not top_has_prop_key:
        return props
    return data
