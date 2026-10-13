"""OPSPILOT-MASTER-RECORD.md must stay UTF-8 without a BOM (append-only safe)."""

from __future__ import annotations

from pathlib import Path

_MASTER = Path("OPSPILOT-MASTER-RECORD.md")


def test_master_record_utf8_no_bom() -> None:
    raw = _MASTER.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "OPSPILOT-MASTER-RECORD.md must not start with UTF-8 BOM"
    raw.decode("utf-8")  # strict
