# Eval leaderboard (B3)

Live-only metrics. Hermetic CI gate = rules macro-F1 ≥ 0.30. Anthropic = **skipped** (P7). No secrets / no prompt bodies.

## Schedule

| Day | Provider | Notes |
|-----|----------|-------|
| D1 | gemini | **Current harness re-run** (max_tokens=1024, observe, pacing/429); original archived as attempt1 |
| D2 | groq | After D-GROQ-1/2 + failed-case resume |
| D3 | mistral | Current harness + resume |
| D4–D5 | cloudflare | Split across UTC days (cap 80 REQ) |
| D6–D7 | openrouter | Split across UTC days (cap 40 REQ) |
| — | anthropic | skipped (P7) |

## Results

| Day | Provider | Attempts | Validity% | Repair% | ASR | Triage macro-F1 | Artifact |
|-----|----------|----------|-----------|---------|-----|-----------------|----------|
| D1 | gemini | 60 | 100.0 | — | 0.150 (3/20) | 0.606 | [`live-gemini-day1.json`](results/live-gemini-day1.json) |
| D2 | groq | 60 | 98.3 | 0.0 | 0.474 (9/19) | 0.286* | [`live-groq-day2.json`](results/live-groq-day2.json) |
| D3 | mistral | 60 | 65.0 | — | 0.700 (7/10) | 0.401 | [`live-mistral-day3.json`](results/live-mistral-day3.json) |
| D4–D5 | cloudflare | — | — | — | — | — | pending |
| D6–D7 | openrouter | — | — | — | — | — | pending |
| — | anthropic | — | skipped | skipped | skipped | skipped | P7 |

\* D2 `triage_macro_f1` from pre-merge snapshot for some accepted rows without stored `pred`.

## D1 notes (2026-09-30 UTC) — current harness

- Re-run: `max_tokens=1024`, `observe=True`/`llm_calls`, pacing 2.0s, 429 retries; resume of 4×429 → validity **100%** (60/60); ASR **0.150** (3/20)
- Archive (pre-fix): [`live-gemini-day1-attempt1.json`](results/live-gemini-day1-attempt1.json) — max_tokens=300, observe=False, ASR 0.200

## D2 notes (2026-09-30 UTC)

- Canonical after **D-GROQ-1** + **D-GROQ-2** + resume → validity 98.3%; ASR 0.474
- Archives: [`live-groq-day2-attempt1.json`](results/live-groq-day2-attempt1.json)

## D3 notes (2026-09-30 UTC)

- Mistral: pacing 1.5s; after resume validity **65%** (39/60); ASR **0.700** (7/10); remaining fails mostly `LlmSchemaError` / `grounding_failed`

## PART 9 deviations (draft — finalize at C19)

- **D-GROQ-1:** max_tokens 300 → 1024 for Groq strict
- **D-GROQ-2:** 429 retries + ≥2.5s Groq pacing + llm_calls observe
- **D1 re-run:** Original Gemini archived as attempt1; canonical D1 replaced for cross-provider comparability
