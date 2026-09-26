# D-012: Hand-Rolled LLM Gateway (No LiteLLM)

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B2

## Context

Need multi-provider routing, retries, metering, structured outputs, and Anthropic budget gate without another heavy dependency.

## Decision

Hand-roll a thin gateway (provider interface + factory + policy). **Must** implement Anthropic prepaid gate (D-023). Do not adopt LiteLLM unless provider count explodes later.

## Alternatives considered

LiteLLM; LangChain; direct per-adapter SDK calls (CURRENT).

## Consequences

More code ownership; clearer portfolio signal; single choke point for zero-spend enforcement.
