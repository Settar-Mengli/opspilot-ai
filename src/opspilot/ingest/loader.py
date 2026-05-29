from pathlib import Path

from opspilot.models.schemas import REQUIRED_INPUT_FIELDS
from opspilot.utils.file_io import read_json_file


def load_raw_items(input_path: str) -> list[dict]:
    payload = read_json_file(Path(input_path))
    if not isinstance(payload, list):
        raise ValueError("Input JSON must be an array of work items")

    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Item at index {idx} is not an object")
        missing_fields = [key for key in REQUIRED_INPUT_FIELDS if key not in item]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(f"Item {item.get('id', idx)} missing required fields: {missing}")

    return payload
