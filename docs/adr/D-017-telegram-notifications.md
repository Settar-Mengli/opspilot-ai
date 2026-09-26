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

## Consequences

Bot token secrets in operator env; never in client bundle.
