"""Turn arg normalization + schema validation (D-031)."""

from __future__ import annotations

from opspilot.agent.turn_parse import (
    collect_key_paths,
    normalize_tool_args,
    parse_raw_turn_dict,
    validate_tool_args,
)


def test_normalize_args_bag() -> None:
    args, err = normalize_tool_args(
        {"kind": "tool", "tool": "draft_reply", "args": {"work_item_id": "wi_abc", "body": "x"}}
    )
    assert err is None
    assert args == {"work_item_id": "wi_abc", "body": "x"}


def test_normalize_arguments_bag() -> None:
    args, err = normalize_tool_args({"kind": "tool", "tool": "draft_reply", "arguments": {"id": "wi_abc", "body": "x"}})
    assert err is None
    assert args == {"id": "wi_abc", "body": "x"}


def test_normalize_parameters_and_input() -> None:
    for key in ("parameters", "input"):
        args, err = normalize_tool_args({"kind": "tool", "tool": "get_message", key: {"id": "wi_1"}})
        assert err is None
        assert args == {"id": "wi_1"}


def test_normalize_flat_top_level() -> None:
    args, err = normalize_tool_args({"kind": "tool", "tool": "draft_reply", "work_item_id": "wi_abc", "body": "hello"})
    assert err is None
    assert args == {"work_item_id": "wi_abc", "body": "hello"}


def test_normalize_conflict_rejects() -> None:
    args, err = normalize_tool_args(
        {
            "kind": "tool",
            "tool": "draft_reply",
            "args": {"work_item_id": "wi_a", "body": "x"},
            "arguments": {"work_item_id": "wi_b", "body": "x"},
        }
    )
    assert args is None
    assert err is not None
    assert err.startswith("args_conflict:")


def test_normalize_identical_bags_ok() -> None:
    payload = {"work_item_id": "wi_a", "body": "x"}
    args, err = normalize_tool_args(
        {"kind": "tool", "tool": "draft_reply", "args": payload, "arguments": dict(payload)}
    )
    assert err is None
    assert args == payload


def test_collect_key_paths_no_values() -> None:
    paths = collect_key_paths({"kind": "tool", "args": {"work_item_id": "SECRET", "body": "NOPE"}})
    assert "kind" in paths
    assert "args" in paths
    assert "args.work_item_id" in paths
    assert "args.body" in paths
    assert "SECRET" not in paths
    assert "NOPE" not in "".join(paths)


def test_parse_raw_turn_dict() -> None:
    data = parse_raw_turn_dict('{"kind":"tool","tool":"search_items","args":{}}')
    assert data is not None
    assert data["tool"] == "search_items"


def test_validate_draft_reply_schema() -> None:
    assert validate_tool_args("draft_reply", {}) == ["missing_work_item_id", "missing_body"]
    assert validate_tool_args("draft_reply", {"work_item_id": "wi_1"}) == ["missing_body"]
    assert validate_tool_args("draft_reply", {"work_item_id": "wi_1", "body": "ok"}) == []
    assert validate_tool_args("draft_reply", {"id": "wi_1", "body": "ok"}) == []


def test_validate_search_and_get_message() -> None:
    assert validate_tool_args("search_items", {}) == []
    assert validate_tool_args("search_items", {"limit": 5}) == []
    assert validate_tool_args("search_items", {"limit": 99}) == ["limit_out_of_range"]
    assert validate_tool_args("search_items", {"limit": "nope"}) == ["invalid_limit"]
    assert validate_tool_args("get_message", {}) == ["missing_id"]
    assert validate_tool_args("get_message", {"id": "wi_1"}) == []
    assert validate_tool_args("get_calendar", {}) == []
    assert validate_tool_args("get_calendar", {"days": 7}) == []
    assert validate_tool_args("get_calendar", {"days": 30}) == ["days_out_of_range"]
    assert validate_tool_args("get_calendar", {"days": "x"}) == ["invalid_days"]
    assert validate_tool_args("send_mail", {}) == ["unknown_tool"]


def test_normalize_empty_and_null_bags() -> None:
    args, err = normalize_tool_args({"kind": "tool", "tool": "search_items", "args": {}})
    assert err is None
    assert args == {}
    args, err = normalize_tool_args({"kind": "tool", "tool": "search_items", "args": None})
    assert err is None
    assert args == {}
    args, err = normalize_tool_args({"kind": "tool", "tool": "search_items", "args": "not-obj"})
    assert args is None
    assert err == "args_bag_not_object:args"


def test_parse_raw_turn_dict_edge_cases() -> None:
    assert parse_raw_turn_dict(None) is None
    assert parse_raw_turn_dict({"kind": "final", "final": "x"}) == {"kind": "final", "final": "x"}
    assert parse_raw_turn_dict("   ") is None
    assert parse_raw_turn_dict("not-json") is None
    assert parse_raw_turn_dict("[1,2]") is None


def test_collect_key_paths_lists() -> None:
    paths = collect_key_paths({"items": [{"id": "SECRET"}]})
    assert "items" in paths
    assert "items[0].id" in paths
    assert "SECRET" not in "".join(paths)


def test_schema_repair_message_content_free() -> None:
    from opspilot.agent.turn_parse import schema_repair_message

    msg = schema_repair_message(tool="draft_reply", errors=["missing_work_item_id", "missing_body"])
    assert "draft_reply" in msg
    assert "missing_work_item_id" in msg
    assert "missing_body" in msg
    assert "SECRET" not in msg
    assert "Friday" not in msg
