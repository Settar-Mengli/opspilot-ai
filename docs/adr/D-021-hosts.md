# D-021: FE Pages-Class + BE Render-Class + Neon; No Custom Domain

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B7

## Context

Zero-spend public demo; free tiers sleep/cold-start.

## Decision

Frontend on Pages-class host; backend on Render-class free web service; Neon for DB. **No custom domain.** Public exposure only at **B7**.

## Alternatives considered

Vercel+Railway earlier; always-on paid; custom domain.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Pages-class FE + Render-class BE + Neon | Zero-spend public |
| (b) Always-on paid | Violates zero-spend |

## Acceptance criteria

- B7: public URL without custom domain; sleep-tolerant design documented.

## Consequences

Cron and healthchecks must tolerate cold starts; SEC gate before public bind.
