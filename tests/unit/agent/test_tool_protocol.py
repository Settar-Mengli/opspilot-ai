"""Tool protocol fragment + error hints (D-031)."""

from __future__ import annotations

from opspilot.agent.tool_protocol import TOOL_SYSTEM_FRAGMENT, tool_error_hint


def test_tool_system_fragment_has_per_tool_schemas() -> None:
    assert "search_items:{query:string" in TOOL_SYSTEM_FRAGMENT
    assert "get_message:{id:string}" in TOOL_SYSTEM_FRAGMENT
    assert "get_calendar:{days?:int" in TOOL_SYSTEM_FRAGMENT
    assert "draft_reply:{work_item_id|id:string, body:string, subject?:string}" in TOOL_SYSTEM_FRAGMENT
    assert "never a Gmail provider/thread id" in TOOL_SYSTEM_FRAGMENT
    assert "exact `id` from search_items/get_message" in TOOL_SYSTEM_FRAGMENT
    assert '"tool":"search_items"' in TOOL_SYSTEM_FRAGMENT
    assert '"query":"project sync"' in TOOL_SYSTEM_FRAGMENT
    assert '"work_item_id":"<exact id from search_items>"' in TOOL_SYSTEM_FRAGMENT
    assert "wi_4ebc" not in TOOL_SYSTEM_FRAGMENT


def test_tool_error_hint_content_free() -> None:
    assert tool_error_hint("not_found") == "use the exact id from search_items or get_message"
    assert tool_error_hint("missing_body") == "body is required"
    assert tool_error_hint("nope") is None
    hint = tool_error_hint("not_found") or ""
    assert "@" not in hint
    assert "subject" not in hint.lower() or "body is required" in (tool_error_hint("missing_body") or "")
