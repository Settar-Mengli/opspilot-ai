# Triage corpus v1 review checklist

## A2 — Independence from rules classifier

- Cases were authored **without reading** `src/opspilot/rules/triage_rules.py` and without mirroring its keyword lists.
- Wording is varied so gold labels are not keyword-derivable from obvious rule triggers.
- After C6, report per-field hit counts (rules vs gold) so the owner can judge leakage at STOP F1-FLOOR.

## Checklist

- [x] N=40 cases; enum coverage across urgency / category / sentiment
- [x] Fictional only (no real PII)
- [x] Attack-free (injection payloads live in redteam dataset)
- [x] `label_version=triage-labels/v1`
- [x] `allowed_evidence_ids` includes case `id`
