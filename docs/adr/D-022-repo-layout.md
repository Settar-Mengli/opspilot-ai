# D-022: Keep src/opspilot + frontend/

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B0

## Context

Monorepo already understood; renaming burns history for no gain.

## Decision

Keep src/opspilot/ backend package and rontend/ Vite app. Add packages under that tree (gateway, domain, etc.) rather than a new top-level layout.

## Alternatives considered

apps/ packages monorepo reshuffle; backend rewrite in Node.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Keep \src/opspilot\ + \rontend/\ | Stable history |
| (b) Monorepo reshuffle | Burn for no gain |

## Acceptance criteria

- Top-level layout unchanged; internal TARGET packages per D-024.

## Consequences

Stable imports; B1 adds __init__.py and package hygiene without move.
