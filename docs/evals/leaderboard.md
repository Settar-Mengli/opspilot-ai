# Eval leaderboard (B3)

Live-only metrics. Hermetic CI gate = rules macro-F1 ≥ 0.30. Anthropic = **skipped** (P7). No secrets / no prompt bodies.

**Primary live metrics (post D-LIVE fix-pass):** validity (accepted/attempts), **accepted-only** triage macro-F1 (n), repair% (successful parse after failed first parse, ≤1/case), ASR option A with n + `blocked_by_defenses`.

## Schedule

| Day | Provider | Notes |
|-----|----------|-------|
| D1 | gemini | Metrics recomputed under D-LIVE definitions (no extra live) |
| D2 | groq | Resume missing-pred + failed ids after D-LIVE metrics fix → **60/60** |
| D3 | mistral | Full re-run after instance-contract prompt (archive prior as attempt1) → **60/60** |
| D4 | cloudflare | **Partial** first **33/60** corpus (triage only); 100% validity (artifact below) |
| D5 | cloudflare | Remaining **7 triage + 20 redteam** (~27) — **B3.1** (D4 used 66/80 REQ) |
| D6 | openrouter | **Pending** — **≤30 cases** (cap 40 REQ/day) — **B3.1** |
| D7 | openrouter | **Pending** — remaining **~30** + resume fails — **B3.1** |
| — | anthropic | skipped (P7) |

## Results (comparable — post D-LIVE-1..11)

| Day | Provider | Validity | Accepted-only F1 | Repair% | ASR (opt A) | Blocked | Artifact |
|-----|----------|----------|------------------|---------|-------------|---------|----------|
| D1 | gemini | 100% (60/60) | 0.606 (n=40) | 0.0 | 0.150 (3/20) | 0 | [`live-gemini-day1.json`](results/live-gemini-day1.json) |
| D2 | groq | 100% (60/60) | 0.613 (n=40) | 0.0 | 0.400 (8/20) | 0 | [`live-groq-day2.json`](results/live-groq-day2.json) |
| D3 | mistral | 100% (60/60) | 0.537 (n=40) | 0.0 | 0.500 (10/20) | 0 | [`live-mistral-day3.json`](results/live-mistral-day3.json) |
| D4 | cloudflare | 100% (33/33) **partial 33/60** | 0.729 (n=33) | 0.0 | N/A (0 redteam) | 0 | [`live-cloudflare-day4.json`](results/live-cloudflare-day4.json) |
| D5 | cloudflare | — | — | — | — | — | **pending** (~27) → B3.1 |
| D6–D7 | openrouter | — | — | — | — | — | **pending** (smoke only) → B3.1 |
| — | anthropic | skipped | skipped | skipped | skipped | skipped | P7 |

Harness: `b3-live/v2`. Pre-closeout smokes (PART 9): Cloudflare 3/3 red-team; OpenRouter 5/5 (`nemotron…:free`) — **not** merged into day artifacts.

## STOP LIVE before D5

Cloudflare UTC-day budget after D4: **66/80 REQ** (first write failed after a successful 33-case run; re-run saved the artifact). **14 REQ remaining — insufficient for D5 (~27).** Wait for next UTC day + owner `go live day 5`.

## Archives / pre-fix footnotes

| Artifact | Note |
|----------|------|
| [`live-gemini-day1-attempt1.json`](results/live-gemini-day1-attempt1.json) | Pre max_tokens/observe fix |
| [`live-groq-day2-attempt1.json`](results/live-groq-day2-attempt1.json) | Pre D-GROQ pacing |
| [`live-mistral-day3-attempt1.json`](results/live-mistral-day3-attempt1.json) | Pre D-LIVE-1 (schema-echo; validity 65%) |

Historical † rows (validity 65% Mistral, stale Groq F1 0.286, repair% >1) are **not comparable** and were replaced by the table above.

## D1 notes (2026-09-30 UTC)

- Recompute-only after D-LIVE metrics honesty (no new Gemini HTTP for refresh)
- Prior live: max_tokens=1024, observe, pacing; validity 100%

## D2 notes (2026-09-30 UTC)

- Resume 22 ids (17 accepted-without-pred triage + failed/incomplete redteam) → validity **100%**; F1 **0.613**; ASR **0.400** (8/20); 24×429 recovered via retries

## D3 notes (2026-09-30 UTC)

- Full re-run after instance-contract prompt + unwrap → validity **100%** (60/60); F1 **0.537**; ASR **0.500** (10/20); repair **0%**
- Archive: attempt1 (65% validity, schema-echo failures)

## D4 notes (2026-09-30 UTC)

- Cloudflare first **33 triage** (`triage-v1-001`…`033`); redteam deferred to D5
- Validity **100%** (33/33); accepted-only F1 **0.729** (n=33); repair **0%**; ASR N/A (no redteam)
- Budget: first run succeeded in-memory then write path bug (`str` vs `Path`) lost the artifact → re-run saved JSON; counters **66/80 REQ**, **38604** tok. D5 needs next UTC day.

## Deviations

See master-record **PART 9** (D-GROQ-1/2, D-MISTRAL-1, D-LIVE-1..11, D-CF-WRITE-1). Live remainder (CF D5 + OpenRouter D6–D7) → **B3.1**.
