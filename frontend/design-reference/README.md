# OpsPilot AI — Design Reference

These are the **approved visual targets** for the OpsPilot redesign. They are static HTML mockups, not application code. Open any file in a browser to see exactly what the corresponding screen should look like.

## How to review B1.5b desktop mockups (11–16)

1. Open each file below in a browser (double-click or drag into Chrome/Edge).
2. Use DevTools responsive mode at **1280×800** and **1440×900** (each mockup also embeds labeled frames at both widths).
3. Confirm **fonts are Poppins (UI) and Lora (prose)** — same Google Fonts import as production [`frontend/src/styles/tokens.css`](../src/styles/tokens.css). If you see system sans/serif only, check network access to `fonts.googleapis.com` / `fonts.gstatic.com`.
4. Confirm three-pane chrome: **icon rail (left) + content + Ask dock (380px right)**.
5. Reply **`mockups approved`** (with any changes to Ask width 360/380/400, rail order, or Items default selection) before Phase 2 app code.

Shared mockup-only sheet: [`_desktop-mockup.css`](_desktop-mockup.css) (not imported by the app). Production `desktop.css` lands in Phase 2.

## Files

### Historical (01–10) — mobile / card-era targets

| File | Screen | Route / Trigger |
|------|--------|-----------------|
| `01-dashboard-desktop.html` | Dashboard (desktop card, ~680) | `/dashboard` (historical) |
| `02-dashboard-mobile.html` | Dashboard (mobile) | `/dashboard` |
| `03-just-ask-me.html` | Conversation panel | "Just ask me" tile → AskPanel |
| `04-the-two-things.html` | Priorities | "The two things" hero → PrioritiesPanel |
| `05-the-full-picture.html` | All items | "The full picture" tile → `/items` |
| `06-what-im-noticing.html` | Insights | "What I'm noticing" tile → `/insights` |
| `07-wrap-up-the-day.html` | Evening summary | "Wrap up the day" ghost link → EveningPanel |
| `08-the-whole-week.html` | Week shape | "The whole week" ghost link → WeekPanel |
| `09-todays-briefing.html` | Daily briefing | "Today's briefing" ghost link → `/briefing` |
| `10-connections.html` | Integrations roadmap | gear icon → `/connections` |

### B1.5b desktop (≥1280 three-pane) — Phase 1 mockups

| File | Screen | Notes |
|------|--------|-------|
| [`11-desktop-dashboard.html`](11-desktop-dashboard.html) | Dashboard | Rail + greeting/tiles + empty docked Ask |
| [`12-desktop-items-split.html`](12-desktop-items-split.html) | All Items | List + detail split; default = first urgent |
| [`13-desktop-ask-populated.html`](13-desktop-ask-populated.html) | Ask populated | Conversation in dock + **FUTURE (B5)** streaming/tools/approval variant |
| [`14-desktop-briefing.html`](14-desktop-briefing.html) | Briefing | Rail Briefing active |
| [`15-desktop-insights.html`](15-desktop-insights.html) | Insights | Rail Insights active |
| [`16-desktop-settings-rail.html`](16-desktop-settings-rail.html) | Settings | Settings in rail bottom group; gear stays Connections |

**Proposed defaults (open for owner at review):** Ask width **380px**; rail top Dashboard / All Items / Insights / Briefing, bottom Connections / Settings; Items default = first urgent (critical→low).

## How these map to the real app

These references use:
- **Lora** (serif) for the assistant's voice — already the app's `--font-prose`.
- **Poppins** (sans) for UI — already the app's `--font-ui`.
- **Tabler icon webfont** (`<i class="ti ti-NAME">`) **for prototype convenience only** on 01–10. B1.5b mockups 11–16 use inline SVG matching **lucide-react** shapes. Map them:

| Tabler (reference) | lucide-react (app) |
|--------------------|--------------------|
| `ti-flame` | `Flame` |
| `ti-message-circle` | `MessageCircle` |
| `ti-eye` | `Eye` |
| `ti-bulb` | `Lightbulb` |
| `ti-moon` | `Moon` |
| `ti-calendar` | `CalendarDays` |
| `ti-file-text` | `FileText` |
| `ti-arrow-left` | `ArrowLeft` |
| `ti-arrow-right` | `ArrowRight` |
| `ti-chevron-right` | `ChevronRight` |
| `ti-volume` | `Volume2` |
| `ti-copy` | `Copy` |
| `ti-microphone` | `Mic` |
| `ti-bell` | `Bell` |
| `ti-settings` | `Settings` |
| `ti-check` | `Check` |
| `ti-alert-triangle` | `AlertTriangle` |
| `ti-users` | `Users` |
| `ti-mail` | `Mail` |
| `ti-clock` | `Clock` |
| `ti-trending-up` | `TrendingUp` |
| `ti-building` | `Building2` |
| `ti-credit-card` | `CreditCard` |
| `ti-message-2` | `MessageSquare` |
| `ti-plug-connected` | `Plug` |
| `ti-sparkles` | `Sparkles` |
| `ti-circle` | `Circle` |

## The breathing orb

Every screen uses the same assistant presence mark: three concentric circles (animated halo `r=24` solid fill, static inner glow `r=18` radial gradient, solid core `r=11`) in a `0 0 56 56` viewBox. The halo breathes via `@keyframes` animating `transform: scale()`, `fill` (sage `#9CAB7A` ↔ olive `#808000`), and `opacity`, over 5s ease-in-out, gated behind `@media (prefers-reduced-motion: no-preference)`. This is the `BulBulAvatar` component, sized via a `size` prop.

## Palette (locked)

- Background: `#141413`
- Text primary: `#FAF9F5` / softer `#EDEBE3`
- Text muted: `#888780` / `#b0aea5` / faint `#7e7d76`
- Olive accent: `#808000` (bright `#a8a832` / `#cfcf5a` for text on dark)
- Sage: `#9CAB7A` (positive `#788C5D`)
- Info blue: `#6A9BCC` / `#8eb1d8`
- Urgency: critical coral `#d85a30`, high amber `#ef9f27`

## Sample data rule

All example content uses only approved fictional companies (Acme Logistics, Northwind Analytics, Stellar Coffee Co, Helix Manufacturing, Vega Health, Sable Insurance, Atlas Realty, Lumen Education, Pinnacle Robotics, Driftwood Media) and generic roles ("the SRE on-call"). No real names, products, geography, or dollar amounts.

## Build rule

Build **one screen per prompt, one commit each.** Never bundle. Verify (tsc, eslint, build) and screenshot against the matching reference file before committing.
