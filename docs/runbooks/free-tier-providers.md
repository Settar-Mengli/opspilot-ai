# Free-tier providers (candidates)

**Status:** Planning aid. Exact quotas change — **VERIFY AT DECISION TIME** in the provider console before locking B2 smoke.

| Provider | Role (TARGET) | Notes |
|----------|---------------|-------|
| Google Gemini API (free) | Primary hosted | Unpaid tier may use prompts for product improvement — accepted for **fictional** data (D3) |
| Groq (free) | Failover hosted | Rate limits vary; verify |
| Ollama (local) | Local / CI optional | No cloud spend; model pull is operator disk/time |
| Rules / rule_based | Always-on fallback | Deterministic; CI default when no key |
| Anthropic (prepaid) | Side channel only | D-023 gate; never default |

Do not treat third-party blog RPM tables as guaranteed. Prefer official console limits on decision day.

See capability-fit audit: [docs/audits/2026-09-25-capability-fit.md](../audits/2026-09-25-capability-fit.md).
