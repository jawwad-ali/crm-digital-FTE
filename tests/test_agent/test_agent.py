"""Tests for agent infrastructure — logging, context, prompts, agent definition, pool."""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── agent/__init__.py — correlation ID + JSON formatter ─────────────────


def test_set_correlation_id_auto():
    """Auto-generates a UUID hex when no argument provided."""
    from agent import set_correlation_id

    cid = set_correlation_id()
    assert len(cid) == 32  # uuid4 hex = 32 chars


def test_set_correlation_id_explicit():
    """Uses the provided value."""
    from agent import set_correlation_id

    cid = set_correlation_id("my-custom-id")
    assert cid == "my-custom-id"


def test_get_correlation_id():
    """Returns the last set value."""
    from agent import get_correlation_id, set_correlation_id

    set_correlation_id("test-123")
    assert get_correlation_id() == "test-123"


def test_json_formatter_with_correlation_id():
    """Correlation ID appears in JSON output when set."""
    from agent import _JSONFormatter, set_correlation_id

    set_correlation_id("fmt-test")
    formatter = _JSONFormatter()
    record = logging.LogRecord("test.logger", logging.INFO, "", 0, "hello world", (), None)
    output = formatter.format(record)
    data = json.loads(output)

    assert data["correlation_id"] == "fmt-test"
    assert data["msg"] == "hello world"
    assert data["level"] == "INFO"


def test_json_formatter_without_correlation_id():
    """No correlation_id field when unset."""
    from agent import _JSONFormatter, _correlation_id

    _correlation_id.set("")
    formatter = _JSONFormatter()
    record = logging.LogRecord("test.logger", logging.INFO, "", 0, "no cid", (), None)
    output = formatter.format(record)
    data = json.loads(output)

    assert "correlation_id" not in data


def test_json_formatter_with_exception():
    """Exception info is included in JSON output."""
    from agent import _JSONFormatter

    formatter = _JSONFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        exc_info = sys.exc_info()
        record = logging.LogRecord("test.logger", logging.ERROR, "", 0, "boom", (), exc_info)
        output = formatter.format(record)

    data = json.loads(output)
    assert "exception" in data
    assert "ValueError" in data["exception"]


# ── agent/context.py — AgentContext + build_context ─────────────────────


def test_agent_context_dataclass():
    """AgentContext stores db_pool and openai_client."""
    from agent.context import AgentContext

    pool = MagicMock()
    client = MagicMock()
    ctx = AgentContext(db_pool=pool, openai_client=client)

    assert ctx.db_pool is pool
    assert ctx.openai_client is client


@patch("agent.context.create_pool", new_callable=AsyncMock)
@patch("agent.context.AsyncOpenAI")
async def test_build_context_with_args(mock_openai_cls, mock_create_pool):
    """build_context with explicit dsn + api_key."""
    from agent.context import AgentContext, build_context

    mock_create_pool.return_value = MagicMock()
    mock_openai_cls.return_value = MagicMock()

    ctx = await build_context(dsn="postgresql://test", openai_api_key="sk-test")

    assert isinstance(ctx, AgentContext)
    mock_create_pool.assert_awaited_once_with(dsn="postgresql://test")
    mock_openai_cls.assert_called_once_with(api_key="sk-test")


@patch("agent.context.create_pool", new_callable=AsyncMock)
@patch("agent.context.AsyncOpenAI")
async def test_build_context_reads_env(mock_openai_cls, mock_create_pool):
    """build_context with None args → reads env vars."""
    from agent.context import build_context

    mock_create_pool.return_value = MagicMock()
    mock_openai_cls.return_value = MagicMock()

    await build_context()

    mock_create_pool.assert_awaited_once_with(dsn=None)
    mock_openai_cls.assert_called_once_with(api_key=None)


# ── agent/prompts.py — SYSTEM_PROMPT ────────────────────────────────────


def test_system_prompt_not_empty():
    from agent.prompts import SYSTEM_PROMPT

    assert len(SYSTEM_PROMPT) > 100


def test_system_prompt_has_escalation_triggers():
    from agent.prompts import SYSTEM_PROMPT

    assert "refund" in SYSTEM_PROMPT.lower()
    assert "0.3" in SYSTEM_PROMPT
    assert "fabricat" in SYSTEM_PROMPT.lower()


def test_system_prompt_has_guardrails():
    from agent.prompts import SYSTEM_PROMPT

    assert "NEVER" in SYSTEM_PROMPT
    assert "knowledge base" in SYSTEM_PROMPT.lower()
    assert "escalate" in SYSTEM_PROMPT.lower()


def test_system_prompt_has_workflow_tools():
    from agent.prompts import SYSTEM_PROMPT

    tools = [
        "find_or_create_customer", "create_ticket",
        "search_knowledge_base", "send_response",
        "save_message", "update_ticket", "log_metric",
    ]
    for tool in tools:
        assert tool in SYSTEM_PROMPT, f"{tool} not in SYSTEM_PROMPT"


# ── agent/customer_success_agent.py — agent definition ──────────────────


def test_agent_name():
    from agent.customer_success_agent import customer_success_agent

    assert customer_success_agent.name == "Customer Success Agent"


def test_agent_has_all_tools():
    from agent.customer_success_agent import customer_success_agent

    assert len(customer_success_agent.tools) == 11


def test_agent_uses_system_prompt():
    from agent.customer_success_agent import customer_success_agent
    from agent.prompts import SYSTEM_PROMPT

    assert customer_success_agent.instructions == SYSTEM_PROMPT


def test_agent_model_is_set():
    from agent.customer_success_agent import customer_success_agent

    assert customer_success_agent.model is not None


@patch("agent.customer_success_agent.Runner.run", new_callable=AsyncMock)
async def test_run_agent(mock_run, agent_context):
    """run_agent delegates to Runner.run and returns final_output."""
    from agent.customer_success_agent import run_agent

    mock_result = MagicMock()
    mock_result.final_output = "Your password can be reset in Settings."
    mock_run.return_value = mock_result

    output = await run_agent(agent_context, "How do I reset my password?")

    assert output == "Your password can be reset in Settings."
    mock_run.assert_awaited_once()


# ── database/pool.py — encode/decode/create_pool ────────────────────────


def test_encode_vector():
    from database.pool import _encode_vector

    assert _encode_vector([1.0, 2.0, 3.0]) == "[1.0, 2.0, 3.0]"


def test_decode_vector():
    from database.pool import _decode_vector

    assert _decode_vector("[1.0, 2.0, 3.0]") == [1.0, 2.0, 3.0]


def test_encode_decode_roundtrip():
    from database.pool import _decode_vector, _encode_vector

    original = [0.123, 0.456, 0.789]
    assert _decode_vector(_encode_vector(original)) == original


@patch("database.pool.asyncpg.create_pool", new_callable=AsyncMock)
async def test_create_pool_with_dsn(mock_create):
    """Explicit dsn is passed to asyncpg.create_pool."""
    from database.pool import create_pool

    mock_create.return_value = MagicMock()
    await create_pool(dsn="postgresql://localhost/test")

    mock_create.assert_awaited_once()
    call_args = mock_create.call_args
    assert call_args[0][0] == "postgresql://localhost/test"


@patch("database.pool.asyncpg.create_pool", new_callable=AsyncMock)
@patch.dict(os.environ, {"DATABASE_URL": "postgresql://env-test"})
async def test_create_pool_reads_env(mock_create):
    """No dsn → reads DATABASE_URL env var."""
    from database.pool import create_pool

    mock_create.return_value = MagicMock()
    await create_pool()

    call_args = mock_create.call_args
    assert call_args[0][0] == "postgresql://env-test"


async def test_init_connection():
    """_init_connection registers pgvector codec on connection."""
    from database.pool import _init_connection

    conn = AsyncMock()
    await _init_connection(conn)

    conn.set_type_codec.assert_awaited_once_with(
        "vector",
        encoder=pytest.importorskip("database.pool")._encode_vector,
        decoder=pytest.importorskip("database.pool")._decode_vector,
        schema="public",
        format="text",
    )
