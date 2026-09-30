# D-013: Native JSON Schema/Mode + Pydantic

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B2, B3

## Context

Insights/triage JSON is fragile; free providers vary in schema support.

## Decision

Prefer provider-native JSON schema/mode where available; always validate with Pydantic. Fail closed to rules/retry policy — never ship unvalidated model JSON as domain state.

## Alternatives considered

Free-form prose parsing; instructor/library wrappers only.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Native JSON schema/mode + Pydantic | Provider-native; validated |
| (b) Free-form parse | Fragile |

## Acceptance criteria

- B2/B3: unvalidated model JSON never becomes domain state; schema failures retry once then fail closed.

## Addendum (B2, 2026-09-29) — structured output contracts

- Prefer native schema/mode where the provider accepts it; always `model_validate` after `extract_json_object`.
- **Gemini** `generationConfig.responseSchema` (generateContent): subset of OpenAPI 3.0 Schema — **no `$ref` / `$defs`**; strip unsupported keywords; never drop property *names* that collide with metadata keywords (e.g. field `title`). Doc: [Gemini API structured output](https://ai.google.dev/gemini-api/docs/structured-output) (`responseMimeType` + `responseSchema`).
- **Groq** strict (`openai/gpt-oss*`): every object needs `additionalProperties: false` and `required` covering all properties (Groq structured-outputs docs). Other Groq models stay `json_object`.
- **json_object** providers (mistral, cloudflare, openrouter): schema reminder in prompt; robust fence/prose extraction; adequate `max_tokens`.
- Schema/format HTTP 400 → one same-provider `json_object` retry (budget debit + `LlmCall` row) then failover.
- **Empty contract:** if the structured task input is non-empty, an empty answer list/object that omits required content is a **validation failure** (insights: `insights` `min_length=1`; triage: all reason fields `min_length=1`). Truly empty insights queue → soft path without LLM. Briefing remains prose (not structured).
