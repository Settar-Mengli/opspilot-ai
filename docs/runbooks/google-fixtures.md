# Google API fixtures (read-only capture)

Sanitized JSON under `tests/fixtures/google/` and scripted LLM turns under `tests/fixtures/llm_turns/`.

## Safety rules

- Addresses must use `@example.test` (or other in-repo fictional domains).
- Subjects/bodies must be exact placeholders (`FIXTURE_SUBJECT`, `FIXTURE_BODY`).
- Opaque ids must be `fx_`-prefixed hashes — never raw Gmail/Calendar ids.
- No `ya29.`, `Bearer `, or refresh-token shapes.
- Automated gate: `tests/unit/test_fixture_safety.py` (CI).

## Capture (operator only; never CI)

```bash
OPSPILOT_CAPTURE_FIXTURES=1 uv run python scripts/capture_google_fixtures.py
```

Requires an existing operator Google credential in the local DB. Script is read-only (history.list / messages.get metadata / events.list). Prints **counts only** — never tokens, bodies, or full hostnames.

After capture, re-run `uv run pytest tests/unit/test_fixture_safety.py -q` before committing.
