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

## Consequences

Eval cases can assert schemas; adapter code shrinks around shared validation.
