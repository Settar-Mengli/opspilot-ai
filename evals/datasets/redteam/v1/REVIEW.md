# Red-team v1 review checklist

- [x] N=20 fictional attacks; no real PII
- [x] Each case has `gold_labels` for the underlying item (A3)
- [x] `attack_targets` subset of urgency/category/sentiment/delimiter_leak/grounding
- [x] Payloads exercise delimiter_breakout, role_spoof, instruction_override, exfil_request, label_coercion
- [x] Hermetic CI asserts neutralization + fail-closed grounding/leak guards — **ASR is live-only** (D-029)
