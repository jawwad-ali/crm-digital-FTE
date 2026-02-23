"""Tests for the FastAPI backend — all 6 endpoints."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _mock_lifespan():
    """Bypass the real lifespan (which needs a live DB) and inject a fake AgentContext."""
    ctx = MagicMock()
    ctx.db_pool = MagicMock()
    app.state.agent_ctx = ctx
    return ctx


@pytest.fixture()
async def client(_mock_lifespan):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    async def test_health_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class TestChat:
    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_chat_happy_path(self, mock_run, client: AsyncClient):
        mock_run.return_value = "Here is how to reset your password."

        resp = await client.post(
            "/api/chat",
            json={"message": "How do I reset my password?", "email": "alice@example.com"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "Here is how to reset your password."
        assert "correlation_id" in data

        # Verify message was formatted with customer context
        call_args = mock_run.call_args
        assert "[Customer: alice@example.com, Channel: web]" in call_args[0][1]

    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_chat_with_channel(self, mock_run, client: AsyncClient):
        mock_run.return_value = "Response"

        resp = await client.post(
            "/api/chat",
            json={"message": "Hi", "email": "bob@test.com", "channel": "gmail"},
        )

        assert resp.status_code == 200
        call_args = mock_run.call_args
        assert "[Customer: bob@test.com, Channel: gmail]" in call_args[0][1]

    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_chat_with_name(self, mock_run, client: AsyncClient):
        mock_run.return_value = "Hello Alice!"

        resp = await client.post(
            "/api/chat",
            json={"message": "Hi", "email": "alice@test.com", "name": "Alice"},
        )

        assert resp.status_code == 200
        assert resp.json()["response"] == "Hello Alice!"

    async def test_chat_missing_email(self, client: AsyncClient):
        resp = await client.post("/api/chat", json={"message": "Hi"})
        assert resp.status_code == 422

    async def test_chat_missing_message(self, client: AsyncClient):
        resp = await client.post("/api/chat", json={"email": "a@b.com"})
        assert resp.status_code == 422

    async def test_chat_empty_body(self, client: AsyncClient):
        resp = await client.post("/api/chat", content=b"")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Ticket
# ---------------------------------------------------------------------------


class TestTicket:
    @patch("api.main.get_ticket")
    async def test_ticket_found(self, mock_tool, client: AsyncClient):
        fake_result = json.dumps({
            "ticket": {"id": "abc", "status": "open"},
            "conversation": {"id": "conv1"},
            "messages": [],
        })
        mock_tool.on_invoke_tool = AsyncMock(return_value=fake_result)

        resp = await client.get("/api/tickets/abc")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ticket"]["id"] == "abc"

    @patch("api.main.get_ticket")
    async def test_ticket_not_found(self, mock_tool, client: AsyncClient):
        mock_tool.on_invoke_tool = AsyncMock(
            return_value=json.dumps({"error": "ticket not found"})
        )

        resp = await client.get("/api/tickets/bad-id")

        assert resp.status_code == 404
        assert resp.json()["error"] == "ticket not found"


# ---------------------------------------------------------------------------
# Customer History
# ---------------------------------------------------------------------------


class TestCustomerHistory:
    @patch("api.main.get_customer_history")
    async def test_customer_found(self, mock_tool, client: AsyncClient):
        fake_result = json.dumps({
            "customer": {"id": "cust1", "name": "Alice"},
            "identifiers": [{"identifier_type": "email", "identifier_value": "a@b.com"}],
            "conversations": [],
            "conversations_by_channel": {},
            "tickets": [],
        })
        mock_tool.on_invoke_tool = AsyncMock(return_value=fake_result)

        resp = await client.get("/api/customers/cust1/history")

        assert resp.status_code == 200
        data = resp.json()
        assert data["customer"]["id"] == "cust1"

    @patch("api.main.get_customer_history")
    async def test_customer_not_found(self, mock_tool, client: AsyncClient):
        mock_tool.on_invoke_tool = AsyncMock(
            return_value=json.dumps({"error": "customer not found"})
        )

        resp = await client.get("/api/customers/bad-id/history")

        assert resp.status_code == 404
        assert resp.json()["error"] == "customer not found"


# ---------------------------------------------------------------------------
# Gmail Webhook
# ---------------------------------------------------------------------------


class TestGmailWebhook:
    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_gmail_happy_path(self, mock_run, client: AsyncClient):
        mock_run.return_value = "Got your email."

        resp = await client.post(
            "/api/webhooks/gmail",
            json={"from_address": "user@gmail.com", "body": "Need help"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "Got your email."
        assert "correlation_id" in data

        call_args = mock_run.call_args
        assert "[Customer: user@gmail.com, Channel: gmail]" in call_args[0][1]

    async def test_gmail_missing_fields(self, client: AsyncClient):
        resp = await client.post("/api/webhooks/gmail", json={"from_address": "a@b.com"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# WhatsApp Webhook
# ---------------------------------------------------------------------------


class TestWhatsAppWebhook:
    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_whatsapp_happy_path(self, mock_run, client: AsyncClient):
        mock_run.return_value = "Got your WhatsApp message."

        resp = await client.post(
            "/api/webhooks/whatsapp",
            json={"from_address": "+15551234567", "body": "Hello"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "Got your WhatsApp message."

        call_args = mock_run.call_args
        assert "[Customer: +15551234567, Channel: whatsapp]" in call_args[0][1]

    async def test_whatsapp_missing_fields(self, client: AsyncClient):
        resp = await client.post("/api/webhooks/whatsapp", json={"body": "Hi"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


class TestCORS:
    async def test_cors_headers_present(self, client: AsyncClient):
        resp = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Starlette reflects the Origin when allow_credentials=True
        assert "access-control-allow-origin" in resp.headers


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_agent_error_returns_json(self, mock_run, _mock_lifespan):
        mock_run.side_effect = RuntimeError("LLM timeout")

        # Use raise_app_exceptions=False so httpx returns the 500 response
        # instead of re-raising the exception caught by our global handler
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/chat",
                json={"message": "Hello", "email": "test@test.com"},
            )

        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "Internal server error"
