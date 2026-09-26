# Amendment — Anthropic prepaid / budget-capped use

**Constraint update:** Prepaid Anthropic credits only; **no further spend**. Anthropic is allowed for **deliberate, gateway-enforced budget-capped** runs (leaderboard, judge calibration, demo quality). **Never default. Never tests/CI.**

Below: revised sections only, then an exact change log.

---

## Revised sections

### Hard constraint (replace item 1)

| Before | After |
|--------|--------|
| Anthropic is pay-per-use: optional adapter only, never required, never used by tests. | Anthropic may use **existing prepaid credits only** (no further purchase). **Not** the default provider. **Forbidden** in unit/API tests and CI. Allowed only via an explicit **opt-in task/profile** + **hard remaining-budget check** in the gateway (e.g. env `OPSPILOT_ANTHROPIC_BUDGET_TOKENS` / `$` cap + cumulative `LlmCall` accounting). When budget is exhausted → fail closed to Gemini/Groq/Ollama, never charge beyond prepaid. |

---

### §2.4 LLM gateway design (revised)

**Default provider order (unchanged intent):**  
`gemini → groq → ollama → rules` (task-dependent). **Anthropic is never in the default ordered list.**

**Add Anthropic as a named, gated profile:**

| Mechanism | Spec |
|-----------|------|
| **Enable flag** | e.g. `OPSPILOT_ANTHROPIC_ENABLED=true` (default `false`) |
| **Budget** | Hard cap: tokens and/or USD remaining from prepaid; stored/updated from `LlmCall` rows + startup env `OPSPILOT_ANTHROPIC_BUDGET_*` |
| **Allowlist tasks** | Only: `leaderboard`, `judge_calibration`, `demo_quality` (or explicit `provider=anthropic` in **operator-only** admin/smoke scripts — not public `/ask`) |
| **Pre-call check** | If not enabled **or** task not allowlisted **or** projected tokens would exceed remaining budget → **do not call**; return structured error / failover to non-Anthropic |
| **Post-call** | Debit budget from usage; if provider returns usage, prefer that over estimates |
| **Tests/CI** | Gateway test double asserts Anthropic client **never constructed**; CI env must omit Anthropic key **or** set `ENABLED=false` and budget `0` |

**Routing policy (revised one-liner):**  
Default path = free tiers + Ollama. Anthropic = **side channel** for measured comparisons and curated demos, behind budget gate.

---

### §2.6 Eval architecture (revised lanes)

| Lane | When | Providers | Anthropic? |
|------|------|-----------|------------|
| **Deterministic** | Always CI | `rule_based` + schema/red-team | **No** |
| **Local model** | CI optional / nightly | Ollama | **No** |
| **Hosted free** | Manual / weekly | Gemini, Groq | **No** |
| **Prepaid quality (new)** | Manual, operator-triggered, budget-capped | Anthropic (allowlisted tasks only) | **Yes**, gateway budget enforced |
| **Judge calibration (revised)** | Manual subset | Prefer Ollama; **optional** Anthropic judge on small labeled set under budget | Anthropic only if explicitly requested + budget left |

**Leaderboard:** free models always; **optional Anthropic column** from prepaid runs, labeled `prepaid / budgeted`, never implied as default prod brain.

---

### §3 ADRs — D-012 / new D-023

**D-012 Gateway (addendum):** Hand-rolled gateway **must** implement Anthropic budget gate; LiteLLM not required for this.

**D-023 — Anthropic prepaid usage (new ADR candidate)**

| | |
|--|--|
| **Context** | Owner has prepaid credits; zero further spend; want teacher/demo quality without making Claude the product default. |
| **Options** | (a) Ban Anthropic entirely (b) Default to Anthropic until credits die (c) Opt-in + hard budget in gateway |
| **Decision** | **(c)** |
| **Consequences** | Demo/leaderboard can use Haiku/Sonnet-class quality sparingly; CI stays free; accidental pytest burns impossible if gate + hermetic fakes hold |
| **Blocks** | M2 gateway acceptance criteria; M3 leaderboard optional column |

---

### §5 Roadmap — affected milestones

**M2 — LLM gateway (add exit criteria)**  
- Anthropic provider module exists but **disabled by default**.  
- Tests: budget=0 or disabled → no HTTP to Anthropic; allowlisted task + budget → call allowed (mocked).  
- Live smoke default = Gemini **or** Ollama; **optional** separate smoke `scripts/smoke_anthropic_budgeted.py` (not CI).

**M3 — Eval platform (add)**  
- Leaderboard supports optional Anthropic row from manual prepaid run.  
- Judge calibration: document Ollama-first; Anthropic calibration run runbook under `docs/runbooks/`.

**M10 — Deploy**  
- Production `.env`: `OPSPILOT_ANTHROPIC_ENABLED=false` unless operator enables for a capped demo window; budget env required if enabled.  
- Public `/ask` must **not** select Anthropic even if enabled (operator-only / eval scripts only) — **INFERRED product preference; confirm with owner**.

**AGENTS.md standing rule (M0 text to lock)**  
- “Never add Anthropic to default routing. Never use Anthropic in tests/CI. Prepaid budget runs only via allowlisted tasks and gateway budget.”

---

### §6 Decisions — revise Anthropic row

| Decision | Options | Recommendation | Blocks |
|----------|---------|----------------|--------|
| Anthropic role | Ban / default / **prepaid gated** | **Prepaid gated (D-023)** | M2, M3 |
| Public Ask may use Anthropic? | Never / only if enabled | **Never for visitors**; operator demo script only | M6, M10 |
| Budget unit | Tokens / USD / both | **Both if possible**; tokens minimum | M2 |

---

## Exact change log (what changed vs prior report)

1. **Hard constraint §1** — From “optional, never required, never tests” → **prepaid-only, budget-gated, never default, never tests/CI**.  
2. **Cut list / zero-spend narrative** — Anthropic is no longer “effectively banned”; it is **rationed prepaid**. Zero *further* spend still holds.  
3. **§2.4 Gateway** — Added enable flag, hard budget, task allowlist, pre/post debit, CI never-construct rule; Anthropic **removed from default failover chain**.  
4. **§2.6 Evals** — Split “hosted” into **free hosted** vs **prepaid quality**; judge calibration Ollama-first with optional Anthropic.  
5. **§3 ADRs** — Added **D-023**; D-012 addendum for budget gate.  
6. **§5 M2/M3/M10 + AGENTS** — New exit criteria, optional smoke script, deploy defaults, Ask policy clarification.  
7. **§6 Owner decisions** — Anthropic decision reframed as **prepaid gated**, plus public-Ask and budget-unit questions.  
8. **Interview / portfolio wording** — Product default brain remains free-tier; Anthropic = **measured teacher/demo under a hard cap** (not “we run on Claude”).  
9. **Unchanged on purpose** — V1 hermetic fix still mandatory (prepaid credits can still be burned by non-hermetic pytest); F1 Anthropic-guard in tests still required; Gemini/Groq/Ollama still primary path; CUT LIST for P6/P7/P10/A5/MCP unchanged; SEC-01/env-only keys unchanged (Anthropic key still server-only).

**One line for PART 2 lock:** *Default inference = Gemini→Groq→Ollama; Anthropic = opt-in, allowlisted, hard-budgeted prepaid only; never tests/CI.*
