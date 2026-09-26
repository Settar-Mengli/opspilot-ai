import sys

import pytest

from opspilot.cli import main


def test_cli_exits_with_code_1_on_validation_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "opspilot",
            "run",
            "--input",
            "tests/fixtures/does_not_exist.json",
            "--output",
            "data/output",
            "--date",
            "2026-05-29",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Input file not found" in captured.out
