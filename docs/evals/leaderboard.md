# Eval leaderboard (B3)

Live-only metrics. Hermetic CI gate = rules macro-F1 ≥ 0.30. Anthropic = **skipped** (P7). No secrets / no prompt bodies.

| Day | Provider | Attempts | Validity% | Repair% | ASR | Triage macro-F1 | Latency p50/p95 (ms) | Artifact |
|-----|----------|----------|-----------|---------|-----|-----------------|----------------------|----------|
| D1 | gemini | 60 | 100.0 | 0.0 | 0.200 (4/20) | 0.612 | 4166 / 12044 | [`live-gemini-day1.json`](results/live-gemini-day1.json) |
| D2 | groq | 60 | 35.0 | 0.0 | 0.500 (2/4) | 0.286 | 69 / 1255 | [`live-groq-day2.json`](results/live-groq-day2.json) |
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
- **Canonical result** = post-fix re-run (`max_tokens=1024`, ASR N/A fixed): validity 35%; JSONL shows 21 success + 39 `429` (RPM), not schema rejects
- **Attempt 1 (superseded):** validity 11.7%, ASR misreported as 0 with 0 accepted red-team — archived [`live-groq-day2-attempt1.json`](results/live-groq-day2-attempt1.json)
- Root cause (not schema keyword rejection): Groq strict `json_schema` returned `http_400` / `json_validate_failed` / `failed_generation=max completion tokens reached…` at `max_tokens=300` after P12 fields; `json_object` retry often recovered until RPM
- `groq_strict_schema(TriagePayload)` meets Groq strict docs (`additionalProperties:false`, all props required); P12 `minimum`/`maximum`/`minLength`/`maxItems` retained
- Day counter after re-run: used 216 REQ / 43453 TOK; remaining 584 / 116547

## PART 9 deviation (draft — finalize at C19)

- **D-GROQ-1:** First Groq D2 published with inflated schema-failure signal; live runner used `max_tokens=300` and `observe=False` (no `llm_calls`). Diagnosis via live probe: not unsupported P12 keywords; constrained-decode token exhaustion. Fix: `TRIAGE_STRUCTURED_MAX_TOKENS=1024`, ASR `rate=null`→N/A when 0 accepted red-team, archive attempt1, replace canonical D2 JSON.
