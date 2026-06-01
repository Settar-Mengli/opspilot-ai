# OpsPilot AI — Design Reference

These are the **approved visual targets** for the OpsPilot redesign. They are static HTML mockups, not application code. Open any file in a browser to see exactly what the corresponding screen should look like.

## Files

| File | Screen | Route / Trigger |
|------|--------|-----------------|
| `01-dashboard-desktop.html` | Dashboard (desktop) | `/dashboard` |
| `02-dashboard-mobile.html` | Dashboard (mobile) | `/dashboard` |
| `03-just-ask-me.html` | Conversation panel | "Just ask me" tile → AskPanel |
| `04-the-two-things.html` | Priorities | "The two things" hero → PrioritiesPanel |
| `05-the-full-picture.html` | All items | "The full picture" tile → `/items` |
| `06-what-im-noticing.html` | Insights | "What I'm noticing" tile → `/insights` |
| `07-wrap-up-the-day.html` | Evening summary | "Wrap up the day" ghost link → EveningPanel |
| `08-the-whole-week.html` | Week shape | "The whole week" ghost link → WeekPanel |
| `09-todays-briefing.html` | Daily briefing | "Today's briefing" ghost link → `/briefing` |
| `10-connections.html` | Integrations roadmap | gear icon → `/connections` |

## How these map to the real app

These references use:
- **Lora** (serif) for the assistant's voice — already the app's `--font-prose`.
- **Poppins** (sans) for UI — already the app's `--font-ui`.
- **Tabler icon webfont** (`<i class="ti ti-NAME">`) **for prototype convenience only.** The real app uses **lucide-react** components. Map them:

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
