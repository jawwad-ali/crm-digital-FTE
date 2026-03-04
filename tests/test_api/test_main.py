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
    @patch("api.main.set_job", new_callable=AsyncMock)
    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_chat_returns_202_with_job(self, mock_run, mock_set_job, client: AsyncClient):
        mock_run.return_value = "Here is how to reset your password."

        resp = await client.post(
            "/api/chat",
            json={"message": "How do I reset my password?", "email": "alice@example.com"},
        )

        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        assert data["retry_after"] == 5

        # Verify run_agent was called via background task
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "[Customer: alice@example.com, Channel: web]" in call_args[0][1]

    @patch("api.main.set_job", new_callable=AsyncMock)
    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_chat_with_channel(self, mock_run, mock_set_job, client: AsyncClient):
        mock_run.return_value = "Response"

        resp = await client.post(
            "/api/chat",
            json={"message": "Hi", "email": "bob@test.com", "channel": "gmail"},
        )

        assert resp.status_code == 202
        call_args = mock_run.call_args
        assert "[Customer: bob@test.com, Channel: gmail]" in call_args[0][1]

    @patch("api.main.set_job", new_callable=AsyncMock)
    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_chat_with_name(self, mock_run, mock_set_job, client: AsyncClient):
        mock_run.return_value = "Hello Alice!"

        resp = await client.post(
            "/api/chat",
            json={"message": "Hi", "email": "alice@test.com", "name": "Alice"},
        )

        assert resp.status_code == 202
        assert resp.json()["status"] == "processing"

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
# Job Polling
# ---------------------------------------------------------------------------


class TestJobPolling:
    @patch("api.main.get_job", new_callable=AsyncMock)
    async def test_job_processing(self, mock_get, client: AsyncClient):
        mock_get.return_value = {"status": "processing"}

        resp = await client.get("/api/jobs/job-1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "job-1"
        assert data["status"] == "processing"
        assert data["retry_after"] == 5
        assert data["response"] is None

    @patch("api.main.get_job", new_callable=AsyncMock)
    async def test_job_completed(self, mock_get, client: AsyncClient):
        mock_get.return_value = {"status": "completed", "response": "Here is your answer."}

        resp = await client.get("/api/jobs/job-2")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["response"] == "Here is your answer."
        assert data["retry_after"] is None

    @patch("api.main.get_job", new_callable=AsyncMock)
    async def test_job_failed(self, mock_get, client: AsyncClient):
        mock_get.return_value = {
            "status": "failed",
            "response": None,
            "error": "An error occurred while processing your request. Please try again.",
        }

        resp = await client.get("/api/jobs/job-3")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["error"] is not None
        assert data["retry_after"] is None

    @patch("api.main.get_job", new_callable=AsyncMock)
    async def test_job_timed_out(self, mock_get, client: AsyncClient):
        """get_job returns a synthetic failed result for stale processing jobs."""
        mock_get.return_value = {
            "status": "failed",
            "response": None,
            "error": "Request timed out. Please try again.",
        }

        resp = await client.get("/api/jobs/job-stale")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert "timed out" in data["error"]

    @patch("api.main.get_job", new_callable=AsyncMock)
    async def test_job_not_found(self, mock_get, client: AsyncClient):
        """Invalid job ID returns 404."""
        mock_get.return_value = None

        resp = await client.get("/api/jobs/nonexistent")

        assert resp.status_code == 404
        assert resp.json()["error"] == "Job not found"

    @patch("api.main.get_job", new_callable=AsyncMock)
    async def test_job_expired(self, mock_get, client: AsyncClient):
        """Job that has expired from Redis (past 1h TTL) returns 404."""
        mock_get.return_value = None

        resp = await client.get("/api/jobs/expired-job")

        assert resp.status_code == 404


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
    @patch("api.main.set_job", new_callable=AsyncMock)
    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_gmail_returns_202_with_job(self, mock_run, mock_set_job, client: AsyncClient):
        mock_run.return_value = "Got your email."

        resp = await client.post(
            "/api/webhooks/gmail",
            json={"from_address": "user@gmail.com", "body": "Need help"},
        )

        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        assert data["retry_after"] == 5

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "[Customer: user@gmail.com, Channel: gmail]" in call_args[0][1]

    async def test_gmail_missing_fields(self, client: AsyncClient):
        resp = await client.post("/api/webhooks/gmail", json={"from_address": "a@b.com"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# WhatsApp Webhook
# ---------------------------------------------------------------------------


class TestWhatsAppWebhook:
    @patch("api.main.set_job", new_callable=AsyncMock)
    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_whatsapp_returns_202_with_job(self, mock_run, mock_set_job, client: AsyncClient):
        mock_run.return_value = "Got your WhatsApp message."

        resp = await client.post(
            "/api/webhooks/whatsapp",
            json={"from_address": "+15551234567", "body": "Hello"},
        )

        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "processing"

        mock_run.assert_called_once()
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
    @patch("api.main.set_job", new_callable=AsyncMock)
    @patch("api.main.run_agent", new_callable=AsyncMock)
    async def test_agent_error_stored_as_failed_job(self, mock_run, mock_set_job, client: AsyncClient):
        """When run_agent raises, _process_chat catches it and stores a failed job."""
        mock_run.side_effect = RuntimeError("LLM timeout")

        resp = await client.post(
            "/api/chat",
            json={"message": "Hello", "email": "test@test.com"},
        )

        # Endpoint still returns 202 — error is in the background task
        assert resp.status_code == 202

        # set_job should have been called twice: once with "processing", once with "failed"
        assert mock_set_job.call_count == 2
        last_call = mock_set_job.call_args_list[-1]
        job_data = last_call[0][2]  # third positional arg is the data dict
        assert job_data["status"] == "failed"
        assert "error" in job_data
