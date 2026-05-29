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

## Tradeoffs Made Intentionally

- Determinism over semantic flexibility in Milestone 1.
- Fast CLI delivery over early UI polish.
- Local-only simplicity over realistic external integration behavior.
- Lean architecture with explicit seams over premature abstraction depth.
