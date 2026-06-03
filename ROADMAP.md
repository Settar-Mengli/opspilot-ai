# OpsPilot Roadmap

This document tracks the phased evolution of OpsPilot from working demo to enterprise platform.

---

## Phase A — Working Demo *(current)*

**Goal:** Demonstrate the product vision with real AI working on sample data, ready to show to selected investors and partners.

**Status:** ✓ Largely complete

**Capabilities:**
- Mobile-first chief-of-staff dashboard
- Two-step onboarding (user name + assistant naming)
- Claude-powered work item triage
- Claude-generated executive briefing
- Today / Tomorrow / Week views
- Open loops with urgency classification
- Quiet states for low-activity days
- Memory chip and notification UI scaffolding
- Voice input UI (interaction layer; recording deferred)
- Keyboard shortcut (Ctrl+K / Cmd+K) for Ask input

**Tech stack:** TypeScript, React, Vite, FastAPI, Python, Anthropic Claude (Haiku), Tailwind-free CSS design system.

---

## Phase B — Deployed Demo with First Integration

**Goal:** Move from localhost to a public URL with one real integration so investors can sign in with their own Google account and see OpsPilot working on their real inbox.

**Scope:**
- Deploy frontend to Vercel (`opspilot.vercel.app` or custom domain)
- Deploy backend to Railway, Render, or Fly.io
- Add Google OAuth flow
- Gmail integration: read inbox, classify emails, surface escalations, draft replies in user's voice
- Per-user data isolation
- Basic authentication (Google sign-in)

**Out of scope (deferred to later phases):**
- Multiple integrations
- Team features
- Billing

---

## Phase C — Operational Platform

**Goal:** Become a real chief-of-staff tool for individual operators, not just a demo.

**Scope:**
- Google Calendar integration (week-ahead intelligence, meeting prep, conflict resolution)
- Slack integration (channel monitoring, mention summarization, draft replies)
- Notion integration (document context, decision memory)
- Real preference learning (the "Pilot remembers" chip becomes truthful)
- End-of-day summary (real, not mocked)
- Ask Pilot becomes a live Claude conversation

---

## Phase D — Enterprise Platform

**Goal:** Make OpsPilot adoptable by companies, not just individuals.

**Scope:**
- Multi-tenant architecture
- Team workspaces with shared context
- BYOK (Bring Your Own Key) — users plug in their own Anthropic, OpenAI, or Gemini API key
- BYOA (Bring Your Own Agent) — enterprises plug in their internal LLM or company-approved agent via Model Context Protocol (MCP)
- Multi-model abstraction — route tasks to the optimal provider per call (cost, capability, latency)
- Microsoft 365 stack (Outlook, Teams, OneDrive)
- Audit logs and SOC 2 readiness
- Admin controls for IT departments

---

## Phase E — Beyond *(speculative)*

**Possible directions:**
- Mobile native apps (iOS, Android)
- Voice-first interface (real voice input + speech output)
- Multi-agent orchestration (specialized sub-agents per domain)
- Public API for third-party builders
- Marketplace for OpsPilot skills and integrations

---

## Integration Backlog

Beyond the Phase B–D integrations, the following are under consideration based on user demand:

**Project & Engineering:** Jira, Linear, Asana, ClickUp, Monday, Trello, GitHub, GitLab, PagerDuty, Opsgenie, Sentry, Datadog

**Customer & Sales:** HubSpot, Salesforce, Pipedrive, Zendesk, Intercom, Freshdesk

**Finance & Ops:** QuickBooks, Xero, Stripe, DocuSign

**Comms & Meetings:** Zoom, Google Meet, Granola, Otter, Fireflies, LinkedIn

---

## Versioning Principle

OpsPilot will not chase feature count. Each phase ships only when the existing experience meets a high bar of polish, reliability, and clarity. Quality of attention > breadth of features.

---

## Planning Session - June 3, 2026 - Conversation Feature, Provider Abstraction & Monetization

### A. Near-term build target (DECIDED)

Provider abstraction seam.

Extend the existing adapter pattern (factory.py, base.py, claude_adapter.py, decision D-004) so provider selection is environment-driven instead of hardcoded.

Provider + model settings to move to env-driven config:
- provider name
- model string
- API key
- optional base URL

Hardcoded provider/model usage currently appears in five places:
- conversation_adapter.py
- evening_adapter.py
- insights_adapter.py
- briefing_adapter.py
- claude_adapter.py

Current hardcoded values include the model string "claude-haiku-4-5-20251001" and ANTHROPIC_API_KEY usage.

Implementation approach:
- Introduce a thin text-generation provider interface plus factory selected by env.
- Migrate the conversation path first.
- Migrate evening/insights/briefing in follow-up passes.

Timing decision:
- Do this before the conversation feature so conversation work is provider-agnostic from the start.

### B. Conversation feature (DECIDED direction, sequenced)

Target: multi-turn conversation in AskPanel with client-side history.

Storage direction:
- Client sends recent turns on each /ask request.
- Backend remains stateless.
- localStorage persistence lands in Phase B.
- Server-side session store is deferred.

Phase A (in-session multi-turn):
- A1: Contract extension with optional history field (backward compatible).
- A2: Adapter assembles multi-turn message list with turn/character caps.
- A3: Frontend sends bounded recent turns and preserves thread continuity.

Phase B (drafts + persistence):
- Optional typed draft payload with plain-answer fallback.
- [[DRAFT]] card UI + Copy button.
- localStorage thread persistence.

Phase C (voice):
- Voice output (read-aloud via Web Speech Synthesis).
- Voice input (mic to transcript into AskPanel).

Cold-resume current state (as of this planning session):
- /ask accepts only {question, assistant_name} and returns {answer}.
- answer_question handles a single question turn today.
- AskPanel already renders messages as a thread.
- AskPanel is conditionally rendered.

### C. Monetization & model-choice (FUTURE / UNDER REVIEW - not building soon)

Staged plan (future/under-review):

Stage 1:
- Flat $4.99/month subscription.
- OpsPilot provides the built-in default hosted model.
- Fair-use cap (for example, message-count limit) to bound costs.
- Default brain remains a hosted frontier API (Claude is current default, swappable via abstraction).
- Local models (for example Ollama) are ruled out as the default to preserve a simple user experience.
- Local models remain acceptable for personal developer use and possible advanced mode later.

Stage 2:
- Model picker by plan tier.
- Users choose among models mapped to subscription tiers.
- Keep flat pricing; no per-token rebilling at this stage.

Stage 3:
- Full metered billing (token usage + cost meter + user spending caps + threshold notifications).
- Highest complexity and financial risk because OpsPilot becomes a payment intermediary that fronts token costs and must enforce real-time caps.
- Do this last, only if revenue and demand justify the infrastructure.

Decision recorded:
- Bring your own key was considered and ruled out for this monetization direction.
- OpsPilot provides the key/access path instead.
- Do not train a model from scratch (not viable for solo development).
- "OpsPilot's own agent" means the existing adapter + prompts + triage context + persona on top of a hosted base model.

### D. Other backlog (carry forward)

- Backend data-shape uplift:
	- TriageRecord lacks real title/subject (AllItemsPage currently shows id as title).
	- No per-item suggested_action.
	- Briefing/evening responses are prose, not structured payloads.
	- WeekPanel uses static data.
	- Dashboard dayShapeLine is static placeholder text.
	- Consider doing this early because conversation quality depends on this data.
- Mobile viewport optimization pass:
	- Prerequisite: locate nine mobile reference HTML files named opspilot_*_mobile.html.
	- Confirmed not present in the repository right now.
- Panel lifecycle standardization:
	- Some panels are conditionally rendered.
	- Some panels use class-toggle visibility.
- Final full repo audit.

### E. Recommended next-session order

1. Provider seam (conversation path first).
2. Conversation Phase A.
3. Backend data-shape uplift.
4. Phase B drafts/copy.
5. Phase C voice.
6. Mobile pass.
7. Panel standardization.
8. Final audit.
