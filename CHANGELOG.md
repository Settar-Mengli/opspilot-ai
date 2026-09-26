# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project follows Semantic Versioning principles for release tags.

## [Unreleased]

### Added

- **B0 docs lock:** session history (`docs/history/`), audit corpus (`docs/audits/`), `OPSPILOT-MASTER-RECORD.md`, ADR set D-001–D-023, rewritten architecture/roadmap (batches B0–B7), runbooks, glossary updates.

### Changed

- Roadmap IDs are **B0–B7** (former M0–M10 nested as workstreams).
- Agent/contributor docs point at master record + ADRs (PROGRESS.md / decisions.md retired).

### Fixed

- Changelog no longer claims a frontend unit/component test suite as shipped. Vitest is installed; **zero** `*.test.*` / `*.spec.*` files exist under `frontend/src` as of HEAD `41a8678` (see baseline audit). Session 3 delivered provider seam + Settings UI + lint fix only.

### Session 3 notes (historical, already on main)

- `e37370e` — env-configurable conversation provider seam
- `628bc17` — frontend settings screen and model guard
- `5f19b77` — roadmap session 3 progress
- `41a8678` — SettingsPage set-state-in-effect lint fix

---

## Earlier history

Prior Unreleased bullets through the command-center / run-history era remain valid as cumulative project history except where corrected above regarding frontend tests. See git log for authoritative chronology.
