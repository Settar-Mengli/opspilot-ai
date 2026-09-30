"""C11-approved free-tier model defaults (owner 2026-09-29).

Single source of truth for code fallbacks when ``*_MODEL`` env is unset.
Must match ``.env.example`` / PART 7 C11. OpenRouter must keep ``:free``.
"""

from __future__ import annotations

GEMINI_DEFAULT_MODEL = "gemini-3.5-flash-lite"
GROQ_DEFAULT_MODEL = "openai/gpt-oss-20b"
MISTRAL_DEFAULT_MODEL = "ministral-3b-2512"
OPENROUTER_DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
CLOUDFLARE_DEFAULT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
OLLAMA_DEFAULT_MODEL = "llama3.2"

DEFAULT_MODELS: dict[str, str] = {
    "gemini": GEMINI_DEFAULT_MODEL,
    "groq": GROQ_DEFAULT_MODEL,
    "mistral": MISTRAL_DEFAULT_MODEL,
    "openrouter": OPENROUTER_DEFAULT_MODEL,
    "cloudflare": CLOUDFLARE_DEFAULT_MODEL,
    "ollama": OLLAMA_DEFAULT_MODEL,
}
