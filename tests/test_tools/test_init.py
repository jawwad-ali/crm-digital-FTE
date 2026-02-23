"""Tests for agent.tools registry — tool list completeness."""

from agent.tools import ALL_TOOLS, US1_TOOLS, US2_TOOLS, US5_TOOLS


def test_us1_tools_count():
    assert len(US1_TOOLS) == 9


def test_us2_tools_count():
    assert len(US2_TOOLS) == 1


def test_us5_tools_count():
    assert len(US5_TOOLS) == 1


def test_all_tools_count():
    assert len(ALL_TOOLS) == 11


def test_all_tools_is_union():
    """ALL_TOOLS contains every tool from US1 + US2 + US5."""
    all_names = {t.name for t in ALL_TOOLS}
    expected = {t.name for t in US1_TOOLS} | {t.name for t in US2_TOOLS} | {t.name for t in US5_TOOLS}
    assert all_names == expected


def test_tool_names():
    """Verify known tool names are present."""
    names = {t.name for t in ALL_TOOLS}
    expected_names = {
        "find_or_create_customer", "get_customer_history",
        "create_ticket", "update_ticket", "get_ticket",
        "search_knowledge_base",
        "save_message", "get_conversation_messages",
        "send_response",
        "escalate_to_human",
        "log_metric",
    }
    assert names == expected_names
