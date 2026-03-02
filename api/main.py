"""FastAPI backend — thin HTTP layer over the Customer Success Agent."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents import RunContextWrapper

from agent import get_correlation_id, set_correlation_id
from agent.context import build_context
from agent.customer_success_agent import run_agent
from agent.tools.customer import get_customer_history
from agent.tools.ticket import get_ticket

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    email: str
    channel: str = "web"
    name: str | None = None


class ChatResponse(BaseModel):
    response: str
    correlation_id: str


class WebhookPayload(BaseModel):
    from_address: str
    body: str


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    app.state.agent_ctx = await build_context()
    logger.info("Agent context created — DB pool, OpenAI client, and Redis ready")
    yield
    if app.state.agent_ctx.redis_client is not None:
        await app.state.agent_ctx.redis_client.aclose()
        logger.info("Redis connection closed")
    await app.state.agent_ctx.db_pool.close()
    logger.info("DB pool closed")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CRM Digital FTE API",
    description="HTTP layer for the Customer Success Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    cid = set_correlation_id()
    logger.info("Chat request — email=%s channel=%s", req.email, req.channel)

    message = f"[Customer: {req.email}, Channel: {req.channel}] {req.message}"
    response = await run_agent(request.app.state.agent_ctx, message)

    return ChatResponse(response=response, correlation_id=cid)


@app.get("/api/tickets/{ticket_id}")
async def ticket_detail(ticket_id: str, request: Request):
    set_correlation_id()
    wrapper = RunContextWrapper(context=request.app.state.agent_ctx)
    result = await get_ticket.on_invoke_tool(wrapper, json.dumps({"ticket_id": ticket_id}))
    data = json.loads(result)

    if "error" in data and data["error"] == "ticket not found":
        return JSONResponse(status_code=404, content={"error": "ticket not found"})

    return data


@app.get("/api/customers/{customer_id}/history")
async def customer_history(customer_id: str, request: Request):
    set_correlation_id()
    wrapper = RunContextWrapper(context=request.app.state.agent_ctx)
    result = await get_customer_history.on_invoke_tool(
        wrapper, json.dumps({"customer_id": customer_id})
    )
    data = json.loads(result)

    if "error" in data and data["error"] == "customer not found":
        return JSONResponse(status_code=404, content={"error": "customer not found"})

    return data


@app.post("/api/webhooks/gmail", response_model=ChatResponse)
async def webhook_gmail(payload: WebhookPayload, request: Request):
    cid = set_correlation_id()
    logger.info("Gmail webhook — from=%s", payload.from_address)

    message = f"[Customer: {payload.from_address}, Channel: gmail] {payload.body}"
    response = await run_agent(request.app.state.agent_ctx, message)

    return ChatResponse(response=response, correlation_id=cid)


@app.post("/api/webhooks/whatsapp", response_model=ChatResponse)
async def webhook_whatsapp(payload: WebhookPayload, request: Request):
    cid = set_correlation_id()
    logger.info("WhatsApp webhook — from=%s", payload.from_address)

    message = f"[Customer: {payload.from_address}, Channel: whatsapp] {payload.body}"
    response = await run_agent(request.app.state.agent_ctx, message)

    return ChatResponse(response=response, correlation_id=cid)
