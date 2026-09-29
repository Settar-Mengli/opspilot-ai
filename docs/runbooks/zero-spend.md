# Zero-spend runbook

## Rules

1. No further paid API purchase.
2. Default providers: `INFERENCE_PROVIDER_ORDER` (Gemini → Groq → … → soft/rules). See [llm-providers.md](llm-providers.md).
3. Anthropic: existing prepaid only; enable flag + allowlist + **token and USD** budget + USD/MTok rates; never default; never tests/CI; never visitor Ask.
4. Fictional data only for demos and seeded mail.
5. Quotas = VERIFY AT DECISION TIME (do not invent RPM/TPM). Unset budget env → remote deny for that provider.
6. **Never print secrets** (`.env` values, tokens, keys).
7. **X4:** Free tiers may train on prompts — minimize sensitive content; fictional data only.
8. **`OPSPILOT_FORCE_RULES` / `OPSPILOT_LLM_DISABLE`:** honor via `llm_allowed()` at **all** call sites (B2). Tests/CI only for FORCE_RULES; never set FORCE_RULES in deploy.

## Operator checklist

- [ ] Free-tier keys configured; Anthropic disabled unless capped allowlisted task
- [ ] Budget caps set after STOP A (`llm_discover` + dashboard) at ≤80% measured
- [ ] Key check Quiet → False (**do not** print `.env`)
- [ ] Pytest green without network LLM
- [ ] Any Anthropic run is an explicit operator script with budget + USD rates set
- [ ] Public/prod: `OPSPILOT_ANTHROPIC_ENABLED=false` unless capped demo window

## Related

- ADR [D-023](../adr/D-023-anthropic-prepaid-gate.md)
- [llm-providers.md](llm-providers.md)
- [free-tier-providers.md](free-tier-providers.md)
- Amendment audit: [docs/audits/2026-09-26-anthropic-amendment.md](../audits/2026-09-26-anthropic-amendment.md)
