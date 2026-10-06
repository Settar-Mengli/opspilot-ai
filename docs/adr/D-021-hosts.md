# D-021: FE Pages-Class + BE Render-Class + Neon; No Custom Domain

- **Date:** 2026-09-26
- **Status:** Accepted (idle — B7 public deploy backlogged PART 21)
- **Blocks:** B7 (backlog)

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

## Addendum — PART 21 (2026-10-06)

Public free-tier deploy (B7) was **dropped from the spine** and kept as backlog. This ADR is **idle** until B7 is revived; revive checklist: [docs/audits/2026-10-06-b7-preaudit.md](../audits/2026-10-06-b7-preaudit.md). Neon remains **CURRENT** for operator demo STOP LIVE (local/operator use). The original decision body above is unchanged.
