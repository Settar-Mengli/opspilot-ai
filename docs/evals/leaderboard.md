# Eval leaderboard (B3)

Live-only metrics. Hermetic CI gate = rules macro-F1 ≥ 0.30. Anthropic = **skipped** (P7). No secrets / no prompt bodies.

**Primary live metrics (post D-LIVE fix-pass):** validity (accepted/attempts), **accepted-only** triage macro-F1 (n), repair% (successful parse after failed first parse, ≤1/case), ASR option A with n + `blocked_by_defenses`.

## Schedule

| Day | Provider | Notes |
|-----|----------|-------|
| D1 | gemini | Current harness; metrics recomputed under D-LIVE definitions (no extra live) |
| D2 | groq | Resume accepted-without-pred triage ids after D-LIVE metrics fix |
| D3 | mistral | Full re-run after instance-contract prompt (archive prior as attempt1) |
| D4 | cloudflare | **≤33 cases** (cap 80 REQ/day; leave headroom) |
| D5 | cloudflare | Remaining **~27** + resume fails |
| D6 | openrouter | **≤30 cases** (cap 40 REQ/day) |
| D7 | openrouter | Remaining **~30** + resume fails |
| — | anthropic | skipped (P7) |

## Results

| Day | Provider | Attempts | Validity% | Repair% | ASR | Triage macro-F1 (accepted) | Artifact |
|-----|----------|----------|-----------|---------|-----|----------------------------|----------|
| D1 | gemini | 60 | 100.0† | —† | 0.150 (3/20)† | 0.606† | [`live-gemini-day1.json`](results/live-gemini-day1.json) |
| D2 | groq | 60 | 98.3† | 0.0† | 0.474 (9/19)† | 0.286†\* | [`live-groq-day2.json`](results/live-groq-day2.json) |
| D3 | mistral | 60 | 65.0† | 1.53†‡ | 0.700 (7/10)† | 0.401† | [`live-mistral-day3.json`](results/live-mistral-day3.json) |
| D4–D5 | cloudflare | — | — | — | — | — | pending |
| D6–D7 | openrouter | — | — | — | — | — | pending |
| — | anthropic | — | skipped | skipped | skipped | skipped | P7 |

### Footnotes — pre-fix / not comparable (STOP LIVE until post-fix refresh)

† **Pre D-LIVE-1..11 harness.** Numbers above are historical snapshots from before instance-contract prompts, accepted-only F1, repair redefinition, ASR option A, and per-HTTP pacing. **Do not rank providers using † rows.**

\* D2 stored F1 kept a **stale** pre-merge value while 17 accepted triage rows lacked `pred` (D-LIVE-2). Accepted-only recompute on available preds was ~0.59 (n=23) — still incomplete until resume.

‡ D3 `repair_pct` > 1 under the old counter (schema_validation + force_json_object events / cases). Post-fix repair ≤1 per case and is recomputed from `repaired` flags.

**Post-fix refresh plan:** Mistral smoke → full D3 archive+replace; Groq resume 17 missing-pred triage ids; Gemini `--recompute-metrics` only. Then publish a comparable table (validity n, accepted-only F1 n, repair%, ASR n, blocked) before D4.

## D1 notes (2026-09-30 UTC) — current harness

- Re-run: `max_tokens=1024`, `observe=True`/`llm_calls`, pacing 2.0s, 429 retries; resume of 4×429 → validity **100%** (60/60); ASR **0.150** (3/20)
- Archive (pre-fix): [`live-gemini-day1-attempt1.json`](results/live-gemini-day1-attempt1.json) — max_tokens=300, observe=False, ASR 0.200

## D2 notes (2026-09-30 UTC)

- Canonical after **D-GROQ-1** + **D-GROQ-2** + resume → validity 98.3%; ASR 0.474
- Archives: [`live-groq-day2-attempt1.json`](results/live-groq-day2-attempt1.json)

## D3 notes (2026-09-30 UTC)

- Mistral: pacing 1.5s; after resume validity **65%** (39/60); ASR **0.700** (7/10); remaining fails mostly `LlmSchemaError` (schema-echo under `properties`) / `grounding_failed` — addressed by D-LIVE-1

## PART 9 deviations (draft — finalize at C19)

- **D-GROQ-1:** max_tokens 300 → 1024 for Groq strict
- **D-GROQ-2:** 429 retries + ≥2.5s Groq pacing + llm_calls observe
- **D1 re-run:** Original Gemini archived as attempt1; canonical D1 replaced for cross-provider comparability
- **D-LIVE-1..11:** instance-contract prompt; metrics honesty; per-HTTP pacer; leaderboard footnotes
