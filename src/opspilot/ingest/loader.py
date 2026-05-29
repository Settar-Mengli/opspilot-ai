import json
from pathlib import Path

from opspilot.models.schemas import InputValidationError, validate_raw_item
from opspilot.utils.file_io import read_json_file


def load_raw_items(input_path: str) -> list[dict]:
    try:
        payload = read_json_file(Path(input_path))
    except FileNotFoundError as exc:
        raise InputValidationError(f"Input file not found: {input_path}") from exc
    except json.JSONDecodeError as exc:
        raise InputValidationError(
            f"Input file is not valid JSON: {input_path} (line {exc.lineno}, column {exc.colno})"
        ) from exc
    except OSError as exc:
        raise InputValidationError(f"Unable to read input file: {input_path}") from exc

    if not isinstance(payload, list):
        raise InputValidationError("Input JSON must be an array of work items")

    for idx, item in enumerate(payload):
        validate_raw_item(item, idx)

    return payload
