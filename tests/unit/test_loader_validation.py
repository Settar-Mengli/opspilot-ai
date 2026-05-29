import json
from pathlib import Path

import pytest

from opspilot.ingest.loader import load_raw_items
from opspilot.models.schemas import InputValidationError


def test_load_raw_items_raises_for_missing_file() -> None:
    with pytest.raises(InputValidationError, match="Input file not found"):
        load_raw_items("tests/fixtures/does_not_exist.json")


def test_load_raw_items_raises_for_invalid_json(tmp_path: Path) -> None:
    bad_json_file = tmp_path / "bad.json"
    bad_json_file.write_text("{not-json}", encoding="utf-8")

    with pytest.raises(InputValidationError, match="Input file is not valid JSON"):
        load_raw_items(str(bad_json_file))


def test_load_raw_items_raises_for_non_string_required_field(tmp_path: Path) -> None:
    payload = [
        {
            "id": "WI-100",
            "source_type": "email",
            "subject_or_title": "Subject",
            "body_or_description": "Body",
            "sender_or_requester": "ops@local",
            "received_at": 20260529,
        }
    ]
    path = tmp_path / "input.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(InputValidationError, match="must be a non-empty string"):
        load_raw_items(str(path))


def test_load_raw_items_raises_for_invalid_tags_shape(tmp_path: Path) -> None:
    payload = [
        {
            "id": "WI-101",
            "source_type": "email",
            "subject_or_title": "Subject",
            "body_or_description": "Body",
            "sender_or_requester": "ops@local",
            "received_at": "2026-05-29T00:00:00Z",
            "tags": "urgent",
        }
    ]
    path = tmp_path / "input.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(InputValidationError, match="field 'tags' must be an array"):
        load_raw_items(str(path))
