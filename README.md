# OpsPilot AI

**Your AI chief of staff.** OpsPilot transforms operational chaos into clarity — surfacing the 2–3 things that need you today, handling the rest, and briefing you like a trusted advisor.

Built with TypeScript, React, FastAPI, and Anthropic Claude.

---

## What It Does Today

OpsPilot ingests operational work items and uses Claude to:

- **Triage** each item by urgency and category
- **Surface "open loops"** that need executive attention
- **Generate a morning briefing** in natural language
- **Present a calm, focused dashboard** that translates hundreds of signals into 2–3 priorities

Mobile-first design. Warm aesthetic. Reads like a memo, not a control panel.

---

## What Makes It Different

Most ops tools show you everything. OpsPilot shows you what matters. The design language is borrowed from Anthropic's own brand — minimalist, warm, high-readability. The voice is borrowed from the world's best chiefs of staff: calm, trustworthy, generous when things are quiet.

---

## Roadmap

OpsPilot is on a path from demo → real product → enterprise platform.

### Phase A — Working Demo *(current)*
- Mobile-first dashboard with onboarding personalization
- Claude-powered triage and briefing
- Beautiful, deployable interface

### Phase B — Deployed Demo with Real Integrations
- Public deployment with authentication
- Gmail integration (read inbox, surface escalations, draft replies)

### Phase C — Operational Platform
- Google Calendar integration (week-ahead intelligence)
- Slack integration (team signal monitoring)
- Notion integration (decision memory, document context)

### Phase D — Enterprise Platform
- Multi-tenant architecture
- Bring Your Own Key (BYOK) for cost control
- Bring Your Own Agent (BYOA) via MCP for compliance

---

## Integration Vision

OpsPilot is designed to wire into the places work actually happens:

**Essential (Phase B–C)** — Gmail, Outlook, Google Calendar, Slack, Microsoft Teams, Notion, Linear

**Expanded (Phase D)** — Jira, Asana, HubSpot, Salesforce, Zendesk, Intercom, GitHub, PagerDuty, Granola, Otter

The integration philosophy: meet users where their work lives. Never make them switch tools to get value.

---

## AI Architecture

OpsPilot uses Anthropic Claude today via a clean adapter pattern (`src/opspilot/adapters/`). The architecture is designed to evolve:

- **Today:** Claude Haiku for classification, briefings, and insights. Rule-based fallback when no API key is configured.
- **Near future:** Multi-model abstraction — route tasks to the optimal model (cost, capability, latency). OpenAI and Gemini adapters will slot in alongside Claude.
- **Enterprise:** BYOK (users bring their own API key) and BYOA (users plug in their own agents via Model Context Protocol).

The principle: **the AI is a commodity layer. The product value is the chief-of-staff workflow, design, trust, and integrations.**

---

## Architecture Overview

opspilot-ai/
├── src/opspilot/         # Python backend (FastAPI)
│   ├── adapters/         # AI provider abstraction
│   ├── pipeline/         # Triage orchestration
│   ├── api/              # REST endpoints
│   └── rules/            # Keyword-based fallback classifier
├── frontend/             # TypeScript + React + Vite
│   ├── src/components/   # UI components
│   ├── src/pages/        # Dashboard, All Items, Briefing
│   └── src/hooks/        # User name, keyboard shortcuts
└── data/                 # Sample inputs and run history

See `docs/ARCHITECTURE.md` for technical detail and `ROADMAP.md` for phase-by-phase plans.

---

## Getting Started

**Prerequisites:** Python 3.10+, Node.js 18+, an Anthropic API key (optional — falls back to rule-based triage)

# Backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .
cp .env.example .env     # add ANTHROPIC_API_KEY
python -m uvicorn opspilot.api.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev

Open `http://localhost:5173`.

---

## AI Provider Configuration

OpsPilot now supports a unified runtime AI configuration for conversation responses:

- `OPSPILOT_AI_PROVIDER` (default: `anthropic`)
- `OPSPILOT_AI_MODEL` (default: `claude-haiku-4-5-20251001`)
- `OPSPILOT_AI_API_KEY` (optional)

If `OPSPILOT_AI_API_KEY` is unset, OpsPilot falls back to `ANTHROPIC_API_KEY` for backward compatibility.

---

## Status

OpsPilot is an active project under development. The current build is a working demo intended to showcase the product vision. Production deployment, authentication, and live integrations are on the roadmap.

For investors and partners interested in early access or collaboration, contact the project owner.
