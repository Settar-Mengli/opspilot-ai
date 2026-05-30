# Decisions

This file records architecture and product decisions in a concise ADR-lite format.

## Decision Template

- ID:
- Date:
- Status: proposed | accepted | superseded
- Context:
- Decision:
- Alternatives considered:
- Consequences:

## D-001: Python-First Local Architecture

- Date: 2026-05-29
- Status: accepted
- Context: The project must be beginner-friendly, local-only, and portfolio-ready.
- Decision: Use a Python-first project structure with local CLI execution.
- Alternatives considered: JavaScript-first stack; notebook-only workflow.
- Consequences: Faster local onboarding, clear packaging path, easier test tooling.

## D-002: Rule-Based AI Simulation First

- Date: 2026-05-29
- Status: accepted
- Context: No paid API keys and no external dependencies in early milestones.
- Decision: Implement deterministic rule-based triage before model-backed approaches.
- Alternatives considered: Immediate LLM integration; hybrid model from day one.
- Consequences: Higher determinism and easier testing; lower semantic flexibility early.

## D-003: CLI-First Vertical Slice

- Date: 2026-05-29
- Status: accepted
- Context: Need delivery signal quickly without UI overhead.
- Decision: Prioritize a runnable CLI workflow before any frontend work.
- Alternatives considered: Dashboard-first implementation.
- Consequences: Faster value delivery; UI deferred to later milestone.

## D-004: Adapter Seam For Future Models

- Date: 2026-05-29
- Status: accepted
- Context: Future model integrations are planned but should not destabilize core logic.
- Decision: Define provider adapter seam so pipeline orchestration stays provider-agnostic.
- Alternatives considered: Direct provider calls in orchestration logic.
- Consequences: Better maintainability and swap capability; slightly more design effort early.

## D-005: Explicit Validation And Error Boundaries

- Date: 2026-05-29
- Status: accepted
- Context: Commit 3 delivered a working slice, but schema checks and failures were too implicit for predictable CLI UX.
- Decision: Add explicit input schema validation, structured pipeline logging, and user-facing exception boundaries in loader, pipeline, and CLI layers.
- Alternatives considered: Keep raw exceptions and rely only on test coverage.
- Consequences: Better debuggability and cleaner failures for local runs; slightly more code around orchestration.

## D-006: Immutable Run History With Latest Compatibility

- Date: 2026-05-29
- Status: accepted
- Context: The project needed run-to-run traceability for automation while preserving compatibility for existing latest-output consumers.
- Decision: Keep writing latest artifacts to `data/output/` and additionally write immutable per-run artifacts to `data/history/runs/YYYY/MM/DD/run-YYYYMMDD-HHMMSS-sss/`.
- Alternatives considered: Replace latest outputs entirely; add a database before proving local history value.
- Consequences: Better auditability and demo traceability with minimal architecture churn; filesystem history may need lifecycle policies later.

## D-007: URL Query Param As Frontend Run Context

- Date: 2026-05-29
- Status: accepted
- Context: Frontend needed to switch between latest and historical snapshots without adding complex state infrastructure.
- Decision: Use `?run_id=` as shared run context across Dashboard, Triage Explorer, and Executive Briefing.
- Alternatives considered: localStorage-only context; new dedicated run-history route before proving UX value.
- Consequences: Simple deep-linkable behavior and refresh persistence; invalid run IDs require graceful fallback UX.

## Tradeoffs Made Intentionally

- Determinism over semantic flexibility in Milestone 1.
- Fast CLI delivery over early UI polish.
- Local-only simplicity over realistic external integration behavior.
- Lean architecture with explicit seams over premature abstraction depth.
