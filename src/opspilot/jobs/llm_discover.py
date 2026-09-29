"""Operator quota / reachability discovery (STOP A). Never prints secret values."""

from __future__ import annotations

import os
import re
import sys
from typing import Any

import httpx

from opspilot.llm.providers.discover_urls import (
    gemini_models_list_url,
    ollama_tags_url,
    openai_compat_models_url,
)
from opspilot.llm.providers.http import default_timeout
from opspilot.llm.routing import provider_order

_SECRET_RE = re.compile(r"(key|token|secret|password|authorization)", re.I)


def _redact_headers(headers: httpx.Headers) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in headers.items():
        if _SECRET_RE.search(k):
            out[k] = "***"
        elif k.lower() in {"retry-after", "x-ratelimit-remaining", "x-ratelimit-limit", "x-ratelimit-reset"}:
            out[k] = v
    return out


def _key_format_warning(provider: str, key: str) -> str | None:
    if provider == "gemini" and key.startswith("AQ."):
        return "Gemini key has unusual AQ. prefix — verify in AI Studio"
    if provider == "anthropic" and key and not key.startswith("sk-ant-"):
        return "Anthropic key does not start with sk-ant- — verify format"
    return None


def _probe_gemini(client: httpx.Client, key: str) -> dict[str, Any]:
    resp = client.get(gemini_models_list_url(), params={"key": key})
    return {
        "reachable": resp.status_code < 500,
        "status_code": resp.status_code,
        "rate_limit_headers": _redact_headers(resp.headers),
        "models_sample": [],
    }


def _probe_openai_compat(client: httpx.Client, *, provider: str, key: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    resp = client.get(openai_compat_models_url(provider), headers=headers)
    models: list[str] = []
    if resp.status_code == 200:
        try:
            data = resp.json()
            for item in (data.get("data") or [])[:5]:
                if isinstance(item, dict) and item.get("id"):
                    models.append(str(item["id"]))
        except Exception:  # noqa: BLE001
            pass
    return {
        "reachable": resp.status_code < 500,
        "status_code": resp.status_code,
        "rate_limit_headers": _redact_headers(resp.headers),
        "models_sample": models,
    }


def discover() -> list[dict[str, Any]]:
    """Probe configured providers; never includes raw key material."""
    results: list[dict[str, Any]] = []
    order = provider_order()
    needs_http = False
    for name in order:
        if name == "gemini" and os.environ.get("GEMINI_API_KEY", "").strip():
            needs_http = True
        elif name in {"groq", "mistral", "openrouter"}:
            env = {"groq": "GROQ_API_KEY", "mistral": "MISTRAL_API_KEY", "openrouter": "OPENROUTER_API_KEY"}[name]
            if os.environ.get(env, "").strip():
                needs_http = True
        elif name == "ollama":
            needs_http = True

    client: httpx.Client | None = httpx.Client(timeout=default_timeout()) if needs_http else None
    try:
        for name in order:
            entry: dict[str, Any] = {"provider": name, "configured": False}
            if name == "gemini":
                key = os.environ.get("GEMINI_API_KEY", "").strip()
                entry["configured"] = bool(key)
                if key and client is not None:
                    warn = _key_format_warning("gemini", key)
                    if warn:
                        entry["warning"] = warn
                    try:
                        entry.update(_probe_gemini(client, key))
                    except Exception as exc:  # noqa: BLE001
                        entry["reachable"] = False
                        entry["error"] = type(exc).__name__
            elif name in {"groq", "mistral", "openrouter"}:
                env = {"groq": "GROQ_API_KEY", "mistral": "MISTRAL_API_KEY", "openrouter": "OPENROUTER_API_KEY"}[name]
                key = os.environ.get(env, "").strip()
                entry["configured"] = bool(key)
                if key and client is not None:
                    try:
                        entry.update(_probe_openai_compat(client, provider=name, key=key))
                    except Exception as exc:  # noqa: BLE001
                        entry["reachable"] = False
                        entry["error"] = type(exc).__name__
            elif name == "cloudflare":
                token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
                account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
                entry["configured"] = bool(token and account)
                entry["note"] = "Dashboard neurons must be recorded manually (STOP A)"
            elif name == "ollama":
                entry["configured"] = True
                if client is not None:
                    try:
                        resp = client.get(ollama_tags_url())
                        entry["reachable"] = resp.status_code < 500
                        entry["status_code"] = resp.status_code
                    except Exception as exc:  # noqa: BLE001
                        entry["reachable"] = False
                        entry["error"] = type(exc).__name__
            results.append(entry)

        results.append(
            {
                "provider": "anthropic",
                "enabled": os.environ.get("OPSPILOT_ANTHROPIC_ENABLED", "").strip().lower()
                in {"1", "true", "yes", "on"},
                "note": "Allowlisted tasks only; never Ask. Quotas/rates VERIFY AT DECISION TIME.",
            }
        )
    finally:
        if client is not None:
            client.close()
    return results


def main() -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    rows = discover()
    for row in rows:
        provider = row.get("provider", "?")
        configured = row.get("configured", row.get("enabled"))
        reachable = row.get("reachable")
        status = row.get("status_code")
        warning = row.get("warning") or row.get("note") or ""
        models = ",".join(row.get("models_sample") or [])
        print(
            f"{provider}\tconfigured={configured}\treachable={reachable}\t"
            f"status={status}\tmodels={models}\t{warning}".rstrip()
        )
        headers = row.get("rate_limit_headers") or {}
        if headers:
            print(f"  rate_limit_headers={headers}")
    print(
        "\nSTOP A: record dashboard quotas (Gemini RPD/RPM, Cloudflare neurons, OpenRouter free) "
        "and approve floor(0.8 × measured) caps before Phase 2."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
