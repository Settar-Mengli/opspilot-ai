# OpsPilot AI — Session 2 Record

> Comprehensive record of this working session. Written so that a future session (any model) or a new colleague can resume cold with full context.

---

## Executive Summary

- **Project:** OpsPilot AI — a mobile-first "AI chief of staff" web app. React 19 / Vite frontend + Python FastAPI backend. Solo developer (Settar Mengli), built via a coding agent in VS Code; Claude acts as the planning / review / prompt-writing layer.
- **Repo:** `opspilot-ai`, GitHub `Settar-Mengli/opspilot-ai`, branch `main`. **Recently moved off OneDrive** (resolved prior git auto-gc friction).
- **Workflow:** Claude writes ONE paste-ready prompt at a time → user runs it in the coding agent (Agent Mode, Default Approvals, never Bypass) → agent auto-commits + pushes → user pastes the report back → Claude gives a short verdict → next prompt. **Git is the source of truth**; the agent's "Keep / N files changed" UI block is stale and is always ignored.
- **Model change mid-session:** The coding agent switched from **Claude Opus 4.6 → GPT 5.3 Codex** (4 Geeks removed Opus 4.6 access). GPT 5.3 passed an accuracy audit and was judged reliable.
- **Headline bug fixed:** A persistent AskPanel mobile "gap" that survived ~6 attempted fixes. **Root cause:** a stale `@media (max-width: 768px)` rule forcing `.ask-panel { height: 90vh }`, silently overriding every base-rule change. Removing it fixed the panel.
- **Shipped this session:** panel/dock opacity fixes, full-screen mobile panels, back navigation + clickable logo, briefing markdown-heading stripping, three-button dashboard action row, tightened dashboard spacing, dead-code cleanup (9 orphaned components + unused CSS).
- **Planning documented:** Full roadmap planned with GPT 5.3 and written to `ROADMAP.md` (commit `ae6af1a`).
- **Decided near-term build:** **Provider abstraction seam** — make model provider/model/key env-configurable (extends the existing adapter pattern), conversation path first. To be done **before** the conversation feature.
- **Decided feature direction:** **Multi-turn conversation** in AskPanel, **client-side history** (backend stays stateless), localStorage persistence later. Phases A → B → C.
- **Monetization (FUTURE / UNDER REVIEW):** staged — Stage 1 flat $4.99/mo with built-in model + fair-use cap; Stage 2 model-picker-by-tier; Stage 3 full metered billing. "Bring your own key" and "train own model" both ruled out.
- **Status at session end:** Working tree clean, all work pushed (HEAD = `ae6af1a`), safe to close VS Code.
- **Flagged prerequisite:** 9 mobile reference HTML files (`opspilot_*_mobile.html`) are NOT in the repo and must be located before the mobile-optimization pass.

---

## Initial Context and Evolution

The session began mid-project, continuing an ongoing build (a prior conversation had been compacted into a summary). OpsPilot AI is a mobile-first "AI chief of staff" that triages operational work items and presents them through a calm, single-voice assistant persona. Claude's role throughout: write precise, paste-ready prompts for the coding agent, review the agent's reports, and give short verdicts before proceeding.

Phases the session moved through:

1. **Bug-fixing** — mobile panel/dock rendering (dominant early focus, especially the AskPanel gap).
2. **Feature work** — back navigation, briefing fix, three-button dashboard row, spacing.
3. **Cleanup** — dead-code removal.
4. **Infrastructure shift** — coding-agent model changed from Claude Opus 4.6 to GPT 5.3 Codex; accuracy audit run.
5. **Strategic planning** — model-provider architecture, monetization, sell/partner strategy, culminating in a documented roadmap.

---

## Key Themes and Development

- **Mobile panel rendering bugs.** Panel/dock opacity (content bleeding through), full-screen panel sizing, and the AskPanel gap. Covered `position: fixed`, `100dvh` vs `100%` vs `90vh`, `align-items: flex-end` vs `stretch`, conditional-render vs class-toggle, CSS cascade/override behavior.
- **Dashboard UI.** Replaced three text "ghost-links" with three small icon+label action buttons (prototyped via visualizer, iterated on text size); tightened vertical spacing to fit one mobile viewport.
- **Briefing page.** Stripped raw markdown `#` headings from summary/body; skipped a title/date line.
- **Navigation.** Added back arrows to full-page screens; made the logo link to `/dashboard`.
- **Code cleanup.** Removed 9 orphaned components + unused CSS; verified with reference checks and a Playwright sanity pass.
- **Tooling/model change.** Coding agent moved to GPT 5.3 Codex; workflow confirmed model-agnostic.
- **Dev environment education.** Explained `.venv`, backend-running vs environment-activated, and that GitHub Desktop doesn't change the repo path.
- **Model-provider architecture.** The strategically central theme: making the AI provider swappable via config.
- **Monetization & business model.** Subscription + multi-model strategy, payment-intermediary risks, staged rollout.
- **Sell/partner strategy.** How a solo builder could sell or partner an app.
- **Roadmap documentation.** Consolidating decisions into `ROADMAP.md`.

---

## Crucial Questions and Answers

- **Why does the AskPanel gap persist despite many fixes?** — A stale `@media (max-width: 768px)` rule set `.ask-panel { height: 90vh }`, overriding the base rule on mobile. Removing it resolved the gap.
- **Is everything saved / can I close VS Code?** (asked repeatedly) — Yes; `git status` showed clean working tree and pushes confirmed each time. The agent's "Keep / N files changed" UI block is stale and ignored.
- **Why did GPT 5.3 recommend client-side history when Claude suggested it first?** — Independently, from reading the code: fits the `AGENTS.md` local-only constraint; thread UI + `messages` state already exist; localStorage already used (`useUserName`, `useAssistantName`).
- **Can I build OpsPilot's own agent instead of paying for the API?** — Building your own *model* from scratch is ruled out (not viable for solo dev). Building your own *agent* on top of an existing model is what you already have. Running your own *engine*: hosted-and-paid (start here), self-hosted open model (at scale), or local/Ollama (personal/dev only).
- **Is the multi-model + $4.99 subscription doable?** — Yes, but staged. Provider abstraction is the prerequisite. Full metered token billing makes OpsPilot a payment intermediary (high complexity/risk) and comes last.
- **Should local models be the default brain?** — No. Requiring users to install/run a local model breaks the "make life simple" promise. Kept for personal dev use / optional advanced choice.
- **Is there a product like OpsPilot?** — The category (AI work/ops assistants) is crowded (OpenAI, Anthropic, Google, Microsoft, plus "AI chief of staff" startups); the specific framing/persona is the user's own. Claude noted its knowledge cutoff and recommended a live web search; **the user declined and said they'd do it themselves.**
- **How do I sell or partner without launching?** — The build itself isn't the asset; buyers/partners want users, unique tech, or the team. Paths: acquisition, partnership (most reachable via partner programs), acqui-hire. Warm intros beat cold outreach. The "won't launch" stance works against visibility, which is often how products get found.
- **Where should planning be stored?** — A markdown file committed to git (`ROADMAP.md`), so it survives and any model can resume cold.

---

## Decisions and Justifications

- **Provider abstraction is the near-term build target, done before the conversation feature.** — An adapter pattern already exists (decision D-004; `factory.py`, `base.py`, `claude_adapter.py`), so this extends an existing seam; doing it first makes the conversation feature provider-agnostic and avoids rework. It's the keystone unlocking model-picker, metering, and monetization.
- **Conversation history stored client-side; backend stays stateless.** — Fits `AGENTS.md` local-only; thread UI + `messages` state already exist; localStorage already used. Server-side session store deferred (rejected as over-engineered for now).
- **Default brain = a hosted frontier API (Claude is current default), not a local model.** — Local models break the "simple" UX. Alternatives: self-hosted open model (deferred to scale), local/Ollama (personal/dev only).
- **Monetization staged (flat-tier → model-picker-by-tier → full metered), marked FUTURE/UNDER REVIEW.** — Full metered billing makes OpsPilot a payment intermediary with financial liability and real-time cap enforcement; flat tiers + message caps deliver ~90% of the felt experience with far less risk. "Bring your own key" ruled out (OpsPilot provides access). Training own model ruled out (not viable for solo dev).
- **Remove 9 orphaned components + unused CSS.** — Confirmed unused via reference checks; clears the surface before the conversation feature.
- **AskPanel rebuilt to conditional-render with `slideUp` (then the `90vh` override removed).** — Matched the working slide-panel mechanism; the override was the true root cause.
- **Three text ghost-links replaced with three icon+label buttons.** — User wanted easily clickable targets; approved after visualizer prototypes; final labels 13px.
- **Continue using GPT 5.3 Codex as the coding agent.** — Passed an accuracy audit; workflow is model-agnostic.

---

## Data, Examples and Evidence

**Key commits (chronological, this session):**

```
7e48713  fix: remove stale mobile height override causing AskPanel top gap
a58896f  feat: replace dashboard ghost-links with three action buttons
7f0c35d  style: tighten dashboard spacing to fit one mobile viewport
55e5ba8  chore: remove orphaned components and unused CSS
ae6af1a  docs: record planning session — provider abstraction, conversation feature, monetization roadmap
```

Earlier in the session the AskPanel fix sequence also produced `d6aa3aa`, `1738b37`, plus panel/dock fixes `ee42763`, `8c565da`, `12dff78`, `4638d45`, and others.

**Root-cause CSS (the AskPanel gap) — removed:**

```css
@media (max-width: 768px) {
  .ask-panel { height: 90vh; max-height: none; }  /* removed — this was the culprit */
}
```

**Current `/ask` backend contract (for cold resume):**

```python
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    assistant_name: str = Field(default="OpsPilot", ...)
# handler returns {"answer": answer}
```

**Answer-layer signature:**

```python
def answer_question(question: str, assistant_name: str = "OpsPilot",
                    triage_records: list[dict[str, Any]] | None = None) -> str:
```

**Hardcoded model/provider locations (5):** `conversation_adapter.py`, `evening_adapter.py`, `insights_adapter.py`, `briefing_adapter.py`, `claude_adapter.py` (model string `"claude-haiku-4-5-20251001"`, `ANTHROPIC_API_KEY` env read).

**Frontend types:** `AskRequest {question, assistant_name}`, `AskResponse {answer}`, `AskMessage {id, role, text, timestamp}`.

**Data shapes:**
- `TriageRecord` — `id, urgency, urgency_reason, category, category_reason, sentiment, sentiment_reason` (**no title/subject field** — UI renders `id` as the title).
- `InsightItem` — `title, body, category`.
- `Capability` — `id, name, category, apps, status, featured, description`.

**Reference document:** `frontend/design-reference/03-just-ask-me.html` (contains draft Copy + read-aloud cues).

---

## Glossary / Definitions

- **`.venv` (virtual environment):** A private, isolated copy of Python inside the project with its own packages, keeping dependencies separate from system/other projects. "Activated" (`(.venv)` prefix) ≠ "backend running."
- **Agent (product context):** A model + prompts + logic + data + tools — the intelligence layer built *on top of* a base model. OpsPilot's agent = adapter + prompts + triage context + persona.
- **Provider abstraction / seam:** A thin interface so the model provider/model/key is selected by config (env var) rather than hardcoded.
- **Stateless vs stateful (server):** Stateless = server remembers nothing between requests (simpler, restart-safe); stateful = server stores session state (needs storage + lifecycle management).
- **Bring Your Own Key (BYOK):** User supplies their own API key and pays providers directly — **ruled out** for OpsPilot.
- **`dvh` (dynamic viewport height):** Mobile viewport height that changes as browser chrome shows/hides; source of the panel-sizing mismatch.
- **Conditional-render vs class-toggle:** Two panel mounting strategies (`if (!open) return null` vs always-in-DOM `.open` class); inconsistency caused gap bugs.

---

## Assumptions, Restrictions and Limits

- **Local-only constraint:** `AGENTS.md` specifies local-only development, no paid API dependency baked in, no real external integrations — shaped the client-side/stateless decision.
- **Solo developer:** No team; rules out training a model from scratch and large infrastructure.
- **Mobile is the target platform:** Desktop must not break, but mobile wins all tradeoffs; only mobile screenshots needed for review.
- **Claude's knowledge cutoff:** Flagged for the market-landscape question; live search recommended but declined by the user.
- **Workflow constraint:** One atomic prompt/commit at a time; git is the source of truth; the agent's "Keep" UI block is stale.
- **Sample data:** Fictional companies/work items only.

---

## Risks, Doubts and Pending Tasks

**Risks identified:**

- **Token growth/latency** from sending conversation history each request (mitigation: turn/char caps).
- **Mixed panel lifecycle patterns** (conditional-render vs class-toggle) risk regressions.
- **Contract drift** if a typed draft payload mixes with plain-answer responses without guards.
- **Monetization financial liability:** metered billing makes OpsPilot a payment intermediary (fronting token costs, real-time cap enforcement, fraud exposure).
- **Default-plan cost risk:** a heavy $4.99 user could exceed their fee in tokens (mitigation: fair-use/message cap).
- **Sell-without-launching risk:** an unlaunched app is a weak asset; visibility is often how products get found.

**Open questions / under review:**

- Provider abstraction depth and exact timing relative to conversation work.
- Conversation persistence scope (localStorage-only vs backend session store).
- Structured draft payload vs plain-text-only response.
- Voice output scope in Phase C.
- Panel lifecycle standardization approach.
- Integration sequencing (aggregator-first vs direct-provider-first).
- Frontend automated test depth.

**Pending tasks / TODOs:**

- **Locate the 9 mobile reference HTML files** (`opspilot_*_mobile.html`) — confirmed NOT in repo; prerequisite for the mobile pass.
- **Backend data-shape uplift:** add real title/subject to `TriageRecord`; per-item `suggested_action`; structured (not prose) briefing/evening responses; real WeekPanel data source; dashboard `dayShapeLine` is a static placeholder.
- **Panel lifecycle standardization.**
- **Final full repo audit.**

---

## Next Steps and Current Status

**Recommended next-session order (documented in `ROADMAP.md`):**

1. **Provider abstraction seam** (conversation path first).
2. **Conversation Phase A** (history contract + adapter assembly + AskPanel continuity).
3. **Backend data-shape uplift** (title/subject/actionability + schema alignment). *(Claude suggested possibly doing this earlier, as conversation quality depends on it — a judgment call, not finalized.)*
4. **Phase B** (draft card + Copy + localStorage persistence).
5. **Phase C** (voice output, voice input).
6. **Mobile-viewport optimization pass** (after locating the reference files).
7. **Panel lifecycle standardization.**
8. **Final full repo audit.**

**Current status at session end:**

- **Working tree clean; all work pushed.** HEAD = `ae6af1a`.
- **Planning fully documented** in `ROADMAP.md` (sections A–E: near-term build, conversation feature, monetization, backlog, next-session order).
- **No application code pending.** The dashboard preview showed the empty/quiet state because the backend had no triage data loaded (not a bug).
- **Confirmed safe to close VS Code.**
- **First task next session:** the provider abstraction seam.
