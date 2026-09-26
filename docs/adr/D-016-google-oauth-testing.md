# D-016: Google OAuth Testing Forever; Operator-Only Gmail

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B4, B7

## Context

Public Gmail connect triggers verification/CASA risk and breaks zero-spend. Demo needs a real inbox path without onboarding visitors.

## Decision

Google OAuth app stays in **Testing** audience forever for the portfolio demo. **Operator-owned** demo Gmail/Calendar only; seed **fictional** mail. Visitors never connect their Gmail.

## Alternatives considered

Publish OAuth app; visitor BYOK Gmail; synthetic JSON forever.

## Consequences

Narrow scopes; stay off restricted-scope production path; sync idempotency (X1) required in B4.
