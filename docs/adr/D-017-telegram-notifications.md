# D-017: Telegram Notifications; Web Push Deferred

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B6

## Context

Morning run needs a notify channel. Full PWA + VAPID push adds ops without portfolio gain on free tiers.

## Decision

Telegram bot notifications for B6 morning run. Web push / full PWA deferred to backlog.

## Alternatives considered

Web push only; email only; no notifications.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Telegram bot | Simple; free; operator-friendly |
| (b) Web push / PWA | VAPID/ops cost; deferred |

## Acceptance criteria

- B6 morning job can send Telegram notify; bot token only in secrets.

## Consequences

Bot token secrets in operator env; never in client bundle.
