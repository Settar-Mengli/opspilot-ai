# Free-tier providers (candidates) — historical

**Status:** Historical planning aid from pre-B2. **Do not use for CURRENT caps or model ids.**

Authoritative sources:

- Models (code fallbacks): `src/opspilot/llm/model_defaults.py`
- Caps / env names: `.env.example` + [llm-providers.md](llm-providers.md)
- Master-record C11 table: [OPSPILOT-MASTER-RECORD.md](../../OPSPILOT-MASTER-RECORD.md) PART 7

| Provider | Role (historical TARGET) | Notes |
|----------|--------------------------|-------|
| Google Gemini API (free) | Primary hosted | Unpaid tier may use prompts for product improvement — accepted for **fictional** data (D3) |
| Groq (free) | Failover hosted | Rate limits vary; verify |
| Ollama (local) | Local / CI optional | No cloud spend; model pull is operator disk/time |
| Rules / rule_based | Always-on fallback | Deterministic; CI default when no key |
| Anthropic (prepaid) | Side channel only | D-023 gate; never default |

Do not treat third-party blog RPM tables as guaranteed. Prefer official console limits on decision day (VERIFY AT DECISION TIME).
