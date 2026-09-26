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

## Consequences

Cron and healthchecks must tolerate cold starts; SEC gate before public bind.
