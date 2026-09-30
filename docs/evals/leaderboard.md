# Eval leaderboard (B3)

Live-only metrics. Hermetic CI gate = rules macro-F1 ≥ 0.30. Anthropic = **skipped** (P7). No secrets / no prompt bodies.

| Day | Provider | Attempts | Validity% | Repair% | ASR | Triage macro-F1 | Latency p50/p95 (ms) | Artifact |
|-----|----------|----------|-----------|---------|-----|-----------------|----------------------|----------|
| D1 | gemini | 60 | 100.0 | 0.0 | 0.200 (4/20) | 0.612 | 4166 / 12044 | [`live-gemini-day1.json`](results/live-gemini-day1.json) |
| D2 | groq | — | — | — | — | — | — | pending |
| D3 | mistral | — | — | — | — | — | — | pending |
| D4–D5 | cloudflare | — | — | — | — | — | — | pending |
| D6–D7 | openrouter | — | — | — | — | — | — | pending |
| — | anthropic | — | skipped | skipped | skipped | skipped | skipped | P7 |

## D1 notes (2026-09-30 UTC)

- Budget preflight: `req_cap=400` `tok_cap=800000`
- After run: used 60 REQ / 17993 TOK; remaining 340 REQ / 782007 TOK
- Red-team ASR per D-029 (accepted outputs only)
