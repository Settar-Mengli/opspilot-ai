# Eval leaderboard (B3)

Live-only metrics. Hermetic CI gate = rules macro-F1 ≥ 0.30. Anthropic = **skipped** (P7). No secrets / no prompt bodies.

| Day | Provider | Attempts | Validity% | Repair% | ASR | Triage macro-F1 | Latency p50/p95 (ms) | Artifact |
|-----|----------|----------|-----------|---------|-----|-----------------|----------------------|----------|
| D1 | gemini | 60 | 100.0 | 0.0 | 0.200 (4/20) | 0.612 | 4166 / 12044 | [`live-gemini-day1.json`](results/live-gemini-day1.json) |
| D2 | groq | 60 | 98.3 | 0.0 | 0.474 (9/19) | 0.286* | — | [`live-groq-day2.json`](results/live-groq-day2.json) |
| D3 | mistral | — | — | — | — | — | — | pending |
| D4–D5 | cloudflare | — | — | — | — | — | — | pending |
| D6–D7 | openrouter | — | — | — | — | — | — | pending |
| — | anthropic | — | skipped | skipped | skipped | skipped | skipped | P7 |

\* D2 `triage_macro_f1` retained from pre-merge snapshot (accepted rows from earlier pass lack stored `pred`); validity/ASR recomputed after failed-case resume.

## D1 notes (2026-09-30 UTC)

- Budget preflight: `req_cap=400` `tok_cap=800000`
- **Comparability caveat:** D1 ran with `max_tokens=300` and `observe=False` (no `llm_calls`). Later D-GROQ fixes raised tokens / enabled observe+429 pacing — do not treat D1 vs D2 as an apples-to-apples provider bakeoff without re-running Gemini under the same runner.

## D2 notes (2026-09-30 UTC)

- Canonical result after **D-GROQ-1** (max_tokens=1024) + **D-GROQ-2** (429 retries ≤3 + Groq ≥2.5s pacing + `observe=True`/`llm_calls`) and resume of 39 failed cases
- Final: validity **98.3%** (59/60); ASR **0.474** (9/19 accepted red-team); `rate_limit_events=16` on resume patch
- Archives: [`live-groq-day2-attempt1.json`](results/live-groq-day2-attempt1.json) (pre-token-fix)

## PART 9 deviations (draft — finalize at C19)

- **D-GROQ-1:** First Groq D2 used `max_tokens=300`; Groq strict returned `json_validate_failed` / `failed_generation=max completion tokens…`. Not a schema-keyword rejection. Fix: `TRIAGE_STRUCTURED_MAX_TOKENS=1024`. ASR `rate=null`→N/A when 0 accepted red-team.
- **D-GROQ-2:** Post-token-fix D2 still ~35% validity with JSONL dominated by `429`. Fix: live runner honors Retry-After / exp backoff (cap 60s), ≤3 retries per case, Groq pacing ≥2.5s, `session_attempt_recorder` + `observe=True`. Resume-merge of failed ids → 98.3% validity.
- **D1 caveat:** Gemini D1 predated both fixes (`max_tokens=300`, `observe=False`).
