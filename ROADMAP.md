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
