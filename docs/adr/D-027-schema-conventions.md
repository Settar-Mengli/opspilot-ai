# D-027: Schema conventions

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B2+ (opportunistic migrations)
- **Related:** D-008, D-009, D-011, D-025

## Context

Persistence mixes `String(64)` timestamps with `DateTime(timezone=True)` on some columns (systems audit B-06). Without conventions, B2+ migrations drift and audit rows risk silent CASCADE deletes.

## Decision

- New time columns = `timestamptz`; existing String timestamps migrate in **B2** via Alembic (G-01). B1.5a does **not** migrate timestamps.
- Business string IDs for domain entities; `bigint` identity for internal rows (G-02).
- `snake_case` plural table names; tokens/money = `integer`/`numeric` (never float); `prompt_version` = `char(64)` sha256.
- No secrets in JSONB; encrypted secrets = `bytea` (B4).
- FK cascade: keep CURRENT / document per migration; no silent CASCADE on audit rows.
- Migrations are operator-applied only (aligns D-011).

## Consequences

- Importers and API remain hermetic under current schemas until B2.
- New models must follow this ADR; reviewers reject float money and secret JSONB.
