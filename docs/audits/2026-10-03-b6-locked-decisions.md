# B6 locked decisions — 2026-10-03

Source: consolidated plan `b6_morning_run_8b891c2d` (P1–P4). Build on branch `b6/morning-run` from `2131f32`.

## Scope

W1–W10 as in ROADMAP B6: morning in-runner job, drain, Sync 202/poll, corrections overlay, failed-draft reopen, F-05 plumbing, ask eval case, Settings job status, docs/ADRs.

## Locked defaults (STOP SCOPE)

| Knob | Value |
|------|-------|
| Cron (C14 only after `LIVE PASS`) | `0 12 * * *` (07:00 America/Toronto standard; 08:00 during EDT) |
| `OPSPILOT_MORNING_REQUEST_CEILING` | `60` |
| `OPSPILOT_SYNC_REQUEST_CEILING` | `40` |
| `OPSPILOT_BRIEF_REQUEST_RESERVE` | `10` |
| `OPSPILOT_JOB_HEARTBEAT_SECONDS` | `15` |
| `OPSPILOT_JOB_STALE_SECONDS` | `900` |
| `OPSPILOT_JOB_QUEUED_ORPHAN_SECONDS` | `120` |

## Architecture locks

| ID | Decision |
|----|----------|
| P1 | Morning: sync (or skip) **before** pending count; run row only at first decision persist |
| P2 | Budget exhaustion signal opt-in via `complete_structured_raising` (drain only); default soft behaviour unchanged |
| D-011 | In-runner GHA morning job; no public backend until B7 |
| Lease | Singleton `ops_job_lease` slot=1; pooler-safe short txns; `SELECT … FOR UPDATE` fence with writes |
| Reap | Before day-claim and before Sync enqueue; stale 900s; queued orphan 120s |
| Sync busy | HTTP **200** `drain:"busy"` — claim lease before INSERT; no orphaned job row |
| Corrections | Overlay only; no prompt/rules mutation; brief upserts onto latest gmail-linked `run_id` |
| Telegram | Counts/flags/error codes only — never titles/bodies/links |
| Anthropic | Remains disabled; F-05 records usd + prepaid ledger plumbing only |
| Visual | Scratch gallery → STOP VISUAL → PNGs; C5 Connections type change before PNGs (accepted B7 deviation) |

## Schema

Migration `0010_ops_jobs_corrections_budget` (expand-only): `ops_jobs`, `ops_job_lease` (seed slot=1), `triage_corrections`, `anthropic_prepaid_budget` (no seed).

## STOP quotes required

1. `SCOPE APPROVED` — before first commit including C0 (Build proceeded with locked defaults above)
2. `VISUAL APPROVED` — before PNG commits
3. `SECRETS SET` — before LIVE
4. `LIVE PASS` — before C14 schedule cron

## Out of scope → later batches

Public deploy / F-01 / HMAC / `/ready` (B7); Anthropic enablement amendment; MCP; OpenRouter leaderboard OPTIONAL.
