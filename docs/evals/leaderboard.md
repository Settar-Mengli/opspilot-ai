# Eval leaderboard (B3)

Live-only metrics. Hermetic CI gate = rules macro-F1 ≥ 0.30. Anthropic = **skipped** (P7). No secrets / no prompt bodies.

| Day | Provider | Attempts | Validity% | Repair% | ASR | Triage macro-F1 | Latency p50/p95 (ms) | Artifact |
|-----|----------|----------|-----------|---------|-----|-----------------|----------------------|----------|
| D1 | gemini | 60 | 100.0 | 0.0 | 0.200 (4/20) | 0.612 | 4166 / 12044 | [`live-gemini-day1.json`](results/live-gemini-day1.json) |
| D2 | groq | 60 | 11.7 | 26.7 | 0.000 (0/0 accepted) | 0.153 | 84 / 1824 | [`live-groq-day2.json`](results/live-groq-day2.json) |
| D3 | mistral | — | — | — | — | — | — | pending |
| D4–D5 | cloudflare | — | — | — | — | — | — | pending |
| D6–D7 | openrouter | — | — | — | — | — | — | pending |
| — | anthropic | — | skipped | skipped | skipped | skipped | skipped | P7 |

## D1 notes (2026-09-30 UTC)

- Budget preflight: `req_cap=400` `tok_cap=800000`
- After run: used 60 REQ / 17993 TOK; remaining 340 REQ / 782007 TOK
- Red-team ASR per D-029 (accepted outputs only)

## D2 notes (2026-09-30 UTC)

- Budget preflight: `req_cap=800` `tok_cap=160000`
- Live runner uses 2s inter-case sleep (free-tier RPM courtesy) + per-case circuit reset
- Validity low: 7/60 accepted; 51 `LlmSchemaError`, 1 exhausted, 1 grounding_failed; 0 red-team accepted → ASR n/a numerator 0
- Day counter after D2 (includes aborted earlier Groq attempts): used 147 REQ / 13830 TOK; remaining 653 / 146170
