# OpsPilot AI — Session 1 Record

**Developer:** Settar Mengli (GitHub: `Settar-Mengli`)
**Repository:** `https://github.com/Settar-Mengli/opspilot-ai` (private)
**Local path:** `C:\Users\setta\OneDrive\Desktop\Git Repository\opspilot-ai`
**Session ended:** Handoff to fresh chat for Phase A execution
**Session assistant:** Claude Opus 4.7 (previous)
**Copilot model in use:** Claude Opus 4.6 High (VS Code + GitHub Copilot)

---

## Session Purpose

Continue development of OpsPilot AI — a mobile-first AI Chief of Staff product — from a compacted prior session. Work included: feature completion, bug fixes, multiple audits, and design of the Phase A redesign (Chief of Staff repositioning).

---

## Product Overview

**OpsPilot AI** is a mobile-first AI Chief of Staff. The user picks an assistant name during onboarding (currently "BulBulJan"). The Chief of Staff greets the user warmly, surfaces what needs attention, and waits for instructions. She is designed to feel like a person, not a dashboard.

**Core philosophy (locked in during this session):**
- A real Chief of Staff doesn't dump data — she offers choices and defers to the boss
- The user is the boss; she is hired to make the boss feel powerful and supported
- She brags quietly about what she filtered ("I held three small things off your queue")
- She gives the gift of time ("Nothing in the next hour")
- She frames the week ("Today is light. Friday is where the week tightens")

---

## Tech Stack

- **Backend:** FastAPI on Python 3.13, `src/opspilot/`
- **AI:** Anthropic Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) — only API key in use
- **Frontend:** React 19 + TypeScript + Vite, `frontend/src/`
- **Data:** JSON files (`data/raw/sample_input.json` has 13 fictional items)
- **No database, no auth, no deployment yet** — local Windows development only

---

## Design System (Locked)

**Palette (Anthropic Dark):**
- Background: `#141413`
- Text primary: `#FAF9F5`
- Accent (olive): `#808000`
- Sage green (positive): `#788C5D`
- Soft blue (info): `#6A9BCC`

**Typography:**
- UI: Poppins (sans-serif)
- Prose: Lora (serif) for warm copy and greetings

**Sample data safety (legal requirement):**
- Only fictional companies from approved list: Acme Logistics, Northwind Analytics, Stellar Coffee Co, Helix Manufacturing, Vega Health, Sable Insurance, Atlas Realty, Lumen Education, Pinnacle Robotics, Driftwood Media
- Zero real names, products, geography, or dollar amounts
- Only generic role references

---

## Work Completed This Session

### 1. Phase 2 Polish — S-Tier Complete (5/5)

All five S-tier features were shipped:

- **#24 Better sample data** — 13 realistic items across incidents, customer, finance, vendor, legal, HR, admin, product
- **#2 Loading skeletons** — Applied to Dashboard, AllItems, Briefing, Insights pages
- **#8 Real evening summary** — `POST /evening-summary` endpoint + `EveningPanel.tsx` slide-up
- **#20 Insights page** — `POST /insights` endpoint with structured JSON output; new page with Refresh button and category-colored chips
- **#14 Voice input** — `useSpeechRecognition` hook using Web Speech API (free, no API key)

Each was implemented as a separate atomic commit, verified with lint/build/tests before push.

### 2. Critical Bug Fixes

**Bug: `/insights` endpoint returned "API key required" despite working key in `.env`**
- Root cause: `main.py` never called `load_dotenv()`. Other endpoints worked only because the key had been manually exported in the shell during earlier sessions
- Fix: Added `from dotenv import load_dotenv; load_dotenv()` at top of `main.py`
- Verification: `Key present in process env: True`, 46/46 tests pass

**Bug B-3: Voice close triggered unwanted AskPanel with garbage text**
- Root cause: `onend` handler in `useSpeechRecognition` fired `onFinalTranscript` callback even when user explicitly cancelled
- Fix: Added `cancelledRef` guard, new `cancel()` method using `abort()` instead of `stop()`
- `App.tsx` `handleVoiceClose` now calls `speech.cancel()` instead of `speech.stop()`

**Bug E-5: Frontend triage validation threw hard error on any malformed record**
- Root cause: `client.ts` used `throw new Error` if `records.length !== payload.length`
- Fix: Changed to `console.warn` and returned filtered valid records; both `getTriage` and `getRunTriage` updated

**Bug A-7: localStorage unguarded crashed in Safari private browsing**
- Root cause: `localStorage.setItem` bare calls in `useUserName.ts` and `useAssistantName.ts`
- Fix: Wrapped both in try/catch with silent fallback to in-memory state

**Security: Prompt injection via `assistant_name` field**
- Root cause: `assistant_name` had no validation, was f-stringed directly into Claude system prompts across all three adapters
- Fix: Added Pydantic `Field` constraints to `AskRequest`, `EveningSummaryRequest`, `InsightsRequest`:
  - `question`: `min_length=1, max_length=2000`
  - `assistant_name`: `min_length=1, max_length=60, pattern=r"^[A-Za-z0-9 .'\-]+$"`
- Verification: 12 validation checks passed including rejection of newlines, colons, oversized input; acceptance of realistic names like "Mr. Smith", "O'Brien", "BulBulJan"

### 3. Three Audits Performed

**Audit 1 (Ask Mode):** Code-review focused, made 3 false claims (data folders committed to git, React 19 beta, index.css line count). Found real issues but was not rigorous.

**Audit 2 (Plan Mode with prior-audit verification):** Verified all 29 prior claims with evidence, refuted the false ones, found the critical new issue: **prompt injection via `assistant_name`**.

**Audit 3 (Production Readiness in Plan Mode):** Wider scope covering error handling, race conditions, accessibility, mobile, data integrity, privacy, dependencies, deployment blockers, testing gaps, demo risk, code quality. Found:
- Critical: Voice cancel bug (B-3), Triage validation crash (E-5), Frontend rejects non-localhost URLs (H-1, deployment blocker)
- High: No fetch timeout, localStorage unguarded (A-7), Multiple panels open simultaneously, Color contrast failures, No body scroll lock on panels, Zero tests for `/ask`/`/evening-summary`/`/insights`
- Medium/Low: Various polish items

### 4. Phase A Redesign — Designed and Approved

The current dashboard was diagnosed as philosophically wrong — it dumps data on screen instead of behaving like a real Chief of Staff. A complete redesign was scoped:

**The New Dashboard:**
1. Header: OpsPilot logo, notification bell, gear icon (new — navigates to `/connections`), assistant pill with avatar + name + breathing dot
2. **Top-nav tabs removed entirely** — navigation flows through choice tiles
3. **New avatar** (`BulBulAvatar.tsx`) — 56px olive-gradient circle with simple figure (white head, shoulders, dot eyes, smile). Reusable component with `size` prop.
4. **Greeting block** (`GreetingBlock.tsx`) — Lora serif, warm:
   - Time-aware salutation (Good morning/afternoon/evening/Working late)
   - Short personal warmth line
   - Headline urgency in human terms
   - "Gift of time" line (optional, only when data supports)
   - "Day's shape" line (Claude-generated)
5. **Four primary choice tiles** (2x2 grid):
   - The two things (olive-highlighted) → opens new `PrioritiesPanel.tsx`
   - Just ask me → opens upgraded `AskPanel.tsx`
   - The full picture → navigates to `/items`
   - What I'm noticing → navigates to `/insights`
6. **Three ghost link tertiary actions:**
   - Wrap up the day → `EveningPanel.tsx`
   - The whole week → new `WeekPanel.tsx`
   - Today's briefing → `/briefing`
7. **Credibility line** (dynamic): "I held N small things off your queue this morning. I'll surface them only if they need you."

**Conversation Upgrade (Prompt 2 scope):**
- Chat history within session (last 10 Q+A pairs, React state only, resets on close)
- Voice output via Web Speech Synthesis API (free, browser-built-in)
- Speaker button on each assistant message
- Drafting capability using `[[DRAFT]]...[[/DRAFT]]` markers in Claude responses
- Frontend detects draft blocks and adds Copy button
- Honest limitation messaging when integrations aren't wired

**Connections Architecture (Prompt 3 scope):**
- New `/connections` route + `ConnectionsPage.tsx`
- Backend `src/opspilot/capabilities/registry.py` — proper typed `Capability` dataclass with `CapabilityStatus` enum
- Backend endpoints `GET /capabilities` and `GET /capabilities/{id}`
- Composio featured prominently at top: wide card, 2px olive border, "Recommended" badge, "One connection. 250+ apps." heading
- Category tiles below: Email, Chat, Calendar, Documents, CRM, Payments
- Each connector shows "Coming soon" modal on click — no real OAuth in Phase A
- Toast notification for "Notify me when ready"

### 5. Prototypes Built

Two HTML prototypes were rendered inline via visualization tool (never committed to repo):
- **v1:** Basic redesign with tiles and time-agnostic greeting
- **v2:** Approved final design with avatar, time-aware greeting, gift-of-time line, day's-shape line, "held three small things" italic line

---

## Non-Negotiable Constraints (Established This Session)

1. **No new API keys.** Only Anthropic key already in `.env`.
2. **No new accounts or paid services.** Web Speech APIs (in + out) are free and browser-built-in.
3. **No real OAuth flows yet.** Connections page is architectural only.
4. **Sample data stays safe.** Only fictional companies from approved list.
5. **Security first.** Pydantic validation on all user input. Try/catch on all I/O. No raw user input flowing into Claude system prompts.
6. **Type safety.** Type hints on all Python functions. No `any` types in TypeScript.
7. **Error handling.** Every fetch has `.catch`. Every async has loading state. No silent failures.
8. **Verify before commit.** Lint + build + tests + git status + smoke test.
9. **Small, atomic commits.** One focused change per prompt = one commit.
10. **No deployment work yet.** That's Phase B.

---

## Commits Made This Session (Recent History)

```
0a91620 fix: three critical stability bugs (voice cancel, triage validation, localStorage guard)
bf21ffc fix: load .env in main.py so all API endpoints see ANTHROPIC_API_KEY
0a1ac73 feat: voice input via Web Speech API - hands-free Ask OpsPilot
0217719 feat: Insights page with cross-cutting pattern analysis from Claude
085c428 feat: backend /insights endpoint for cross-cutting pattern analysis
387d2a8 feat: clickable evening summary with Claude-generated end-of-day recap
```

Plus commit after Phase A input validation fix: `fix: input validation on /ask, /evening-summary, /insights to prevent prompt injection and unbounded inputs`

---

## Handoff to Fresh Chat

At session end, work was handed off to a fresh Claude chat with a comprehensive handoff document covering:
- User profile and working style
- Product philosophy and design decisions
- Complete tech stack and file inventory
- Recent fixes and outstanding audit findings
- The full Phase A redesign spec (dashboard, conversation upgrade, connections architecture)
- Non-negotiable constraints
- Working rhythm expectations

**Handoff Q&A rounds:**
1. Fresh Claude read handoff, searched past conversations, produced ~20 clarifying questions
2. Previous Claude (session 1) answered every question with full context: tile behavior, dynamic vs static copy, avatar SVG spec, routing changes, voice output settings, memory scope, drafting UI, modal patterns, Composio treatment, `CapabilityRegistry` structure, backend endpoint design, sequencing (three prompts not one), and audit finding disposition
3. Fresh Claude asked one follow-up about greeting copy: hardcoded vs computed. Answered: prototype was hardcoded placeholder, real implementation will use `/greeting` backend endpoint (Prompt 2 scope), with `GreetingBlock` component built props-driven in Prompt 1 with temporary strings
4. Fresh Claude asked build-sequence question: props-driven component now, swap to endpoint next, two commits not one. Confirmed correct.

---

## Phase A Roadmap (Locked)

**Prompt 1: Dashboard redesign + BulBulAvatar + GreetingBlock scaffolding**
- Replace `DashboardPage.tsx`
- Create `BulBulAvatar.tsx` (reusable, `size` prop)
- Update `AssistantPill.tsx` to use new avatar
- Create `GreetingBlock.tsx` (props-driven with temporary strings from local triage)
- Add time-aware salutation logic in `frontend/src/utils/greeting.ts`
- Wire four tiles + three ghost links
- Remove top-nav tabs from `App.tsx`
- Add gear icon → `/connections`
- Create stub `/connections` route
- Create new `PrioritiesPanel.tsx` and `WeekPanel.tsx`
- Hide bottom Ask input bar
- Fix `<title>frontend</title>` → `<title>OpsPilot AI</title>`
- Comprehensive verification

**Prompt 2: Conversation upgrade + `/greeting` endpoint**
- Add `/greeting` backend endpoint (Claude-generated greeting from triage)
- Swap `GreetingBlock` data source to `/greeting`
- Upgrade `AskPanel.tsx` with chat history (React state, last 10 pairs)
- Add Web Speech Synthesis for voice output
- Speaker button on each assistant message
- Update `/ask` to accept conversation history
- Update `conversation_adapter.py` for `[[DRAFT]]` markers
- Frontend detects drafts + adds Copy button
- Verify voice input still works with new chat layout

**Prompt 3: Connections architecture**
- Create `src/opspilot/capabilities/registry.py` with typed `Capability` dataclass
- Add `GET /capabilities` and `GET /capabilities/{id}` endpoints
- Create `frontend/src/pages/ConnectionsPage.tsx`
- Create connector card components in `frontend/src/components/capabilities/`
- Composio featured card treatment
- Modal for each "Connect" click
- Toast for "Notify me when ready"

**Between each prompt:** verify → smoke test → commit → push. Three commits, three known-good rollback points.

---

## Working Rhythm (Established)

- **One large strategic Copilot prompt per session** (not multiple small ones)
- Each prompt: full design intent, file boundaries, security requirements, verification gates, "After You Finish" structured report, "How to Run" section
- **Copilot mode:** Agent Mode (Plan Mode for diagnostics only)
- **Approvals:** Default (never Bypass Approvals — that caused near-data-loss earlier)
- **Model:** Claude Opus 4.6 High
- **Review edits:** always review, never auto-accept
- **If Copilot hits iteration limit ("Continue?"):** Click Pause, read what it did, don't blindly continue
- **After Copilot finishes:** user brings full report to Claude → Claude reviews carefully → approve or flag → user commits and pushes → smoke test → next prompt

---

## Key Lessons Learned

1. **Every prompt must specify approval mode at the top.** Bypass Approvals once nearly caused data loss.
2. **Plan Mode ≠ Ask Mode.** Plan Mode requires evidence-backed findings and is more rigorous.
3. **First audit was wrong on 3 of 29 claims.** Always re-verify audits.
4. **`load_dotenv()` in main.py is non-optional.** Uvicorn doesn't auto-load `.env` for API endpoints.
5. **ESLint's `react-hooks/set-state-in-effect` is strict.** Use lazy `useState(() => ...)` init or conditional render mount/unmount pattern to avoid.
6. **Test count assertions matter.** Changing sample data from 6 to 13 items would have broken tests that hardcoded `== 6`.
7. **Prompt injection via user-controlled fields is real.** `assistant_name` was flowing directly into Claude system prompts.
8. **Frontend "shows nothing" often means backend not running or env not loaded.** Diagnose environment before assuming code bugs.
9. **Copilot invents "improvements" if not tightly scoped.** Explicit "do not touch" lists prevent scope creep.
10. **Redesign > incremental polish** when a product's philosophy is wrong.

---

## Files Currently in Repository (Post-Session)

**Backend (`src/opspilot/`):**
- `api/main.py` — 8 endpoints with Pydantic validation and `load_dotenv()`
- `adapters/` — `claude_adapter.py`, `briefing_adapter.py`, `conversation_adapter.py`, `evening_adapter.py`, `insights_adapter.py`, `rule_based.py`, `base.py`, `factory.py`
- `pipeline/run_daily_ops.py`
- `rules/triage_rules.py`
- `models/schemas.py`
- `history/run_history.py`
- `ingest/loader.py`, `normalizer.py`
- `nlp/action_extractor.py`, `response_drafter.py`, `briefing_generator.py`
- `utils/file_io.py`, `logging_utils.py`
- `cli.py`

**Frontend (`frontend/src/`):**
- `pages/DashboardPage.tsx`, `AllItemsPage.tsx`, `InsightsPage.tsx`, `BriefingPage.tsx`
- `components/Onboarding.tsx`, `AskPanel.tsx`, `EveningPanel.tsx`, `VoiceOverlay.tsx`, `MobileDock.tsx`, `Greeting.tsx`, `OpenLoop.tsx`, `EveningSummary.tsx`, `HandledBar.tsx`, `MemoryChip.tsx`, `WeekView.tsx`, `QuietState.tsx`, `Brand.tsx`, `AssistantPill.tsx`, `HealthBell.tsx`, `NotifyPanel.tsx`, `AskPilot.tsx`
- `components/skeletons/LoopSkeleton.tsx`, `BriefingSkeleton.tsx`, `InsightCardSkeleton.tsx`
- `hooks/useUserName.ts`, `useAssistantName.ts`, `useGlobalShortcut.ts`, `useSpeechRecognition.ts`
- `api/client.ts`, `types.ts`
- `utils/observations.ts`
- `App.tsx`, `main.tsx`, `index.css` (~1357 lines)

**Config and Data:**
- `.env` (gitignored, contains `ANTHROPIC_API_KEY`)
- `.env.example`
- `.gitignore` (properly excludes `data/output/`, `data/history/`, `.env`, `__pycache__`)
- `pyproject.toml`
- `frontend/package.json`
- `data/raw/sample_input.json` (13 fictional items)
- `docs/architecture.md` (stale — flagged for future doc cleanup)
- `README.md`, `ROADMAP.md`, `CHANGELOG.md`, `PROGRESS.md`, `AGENTS.md`, `CONTRIBUTING.md`

---

## What's Next (Beyond Phase A)

**Phase B — Deployment**
- Fix frontend `sanitizeBaseUrl` to accept configured production URLs
- CORS configuration for production domains
- Deploy backend to Railway
- Deploy frontend to Vercel
- Environment-driven configuration

**Phase C — Real Integrations (later)**
- Composio as strategic first integration
- Or one-at-a-time: Gmail, Slack, Google Calendar
- Each is its own focused engineering project
- OAuth flows, security review, undo logic, error handling

**Phase D — Multi-User (much later)**
- Persistence layer (SQLite → Postgres)
- Authentication (Auth0 or self-hosted)
- Multi-tenancy in `CapabilityRegistry`

---

## Session Metadata

**Chat length:** Long (compacted mid-session)
**Reason for handoff:** Context length approaching drift threshold; Phase A redesign deserves fresh planning context
**Handoff method:** Comprehensive markdown handoff + Q&A rounds between fresh Claude and session Claude to reach ~100% recovery
**Final action:** Fresh Claude confirmed to proceed with three-deliverable response (vision, roadmap, Prompt 1)
