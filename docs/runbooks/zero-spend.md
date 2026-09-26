# Zero-spend runbook

## Rules

1. No further paid API purchase.
2. Default providers: Gemini → Groq → Ollama → rules (TARGET gateway).
3. Anthropic: existing prepaid only; enable flag + allowlist + **token and USD** budget; never default; never tests/CI; never visitor Ask.
4. Fictional data only for demos and seeded mail.
5. Quotas = VERIFY AT DECISION TIME (do not invent RPM/TPM).

## Operator checklist

- [ ] `.env` keys for Anthropic / paid paths commented out for daily work
- [ ] Key check Quiet → False
- [ ] Pytest green without network LLM
- [ ] Any Anthropic run is an explicit operator script with budget env set
- [ ] Public/prod: `OPSPILOT_ANTHROPIC_ENABLED=false` unless capped demo window

## Related

- ADR [D-023](../adr/D-023-anthropic-prepaid-gate.md)
- [free-tier-providers.md](free-tier-providers.md)
- Amendment audit: [docs/audits/2026-09-26-anthropic-amendment.md](../audits/2026-09-26-anthropic-amendment.md)
