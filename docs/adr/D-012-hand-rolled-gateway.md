# D-012: Hand-Rolled LLM Gateway (No LiteLLM)

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B2

## Context

Need multi-provider routing, retries, metering, structured outputs, and Anthropic budget gate without another heavy dependency or LangChain overlap.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Hand-rolled gateway in llm/ | More code ownership; clear portfolio signal; exact policy control |
| (b) LiteLLM | Faster multi-provider; less control; extra dep |
| (c) Keep per-adapter SDK calls | CURRENT pain (AI-01); non-hermetic risk |

## Decision

**(a)** Hand-roll thin gateway (complete / stream / complete_json). **Must** implement Anthropic prepaid gate (D-023). No LiteLLM unless provider count explodes later.

## Acceptance criteria

- B2: fake-provider unit tests; 429/Retry-After failover tested; LlmCall persisted; Anthropic disabled/budget=0 never constructs client in CI.
- Default route excludes Anthropic; X4 minimization applied to logged prompt bodies on free tiers.

## Consequences

More ownership code; single choke point for zero-spend enforcement.

## Blocks

B2.

## Addendum (B2, 2026-09-29)

- Provider clients: Gemini **native REST** (`generativelanguage.googleapis.com`); one **OpenAI-compatible** httpx client class for groq / mistral / cloudflare / openrouter / ollama; Anthropic **SDK only** behind D-023.
- Official provider SDKs beyond Anthropic only via a future ADR addendum if REST proves insufficient.
- Default `INFERENCE_PROVIDER_ORDER` excludes Anthropic; final fallback is rules/soft/template.
