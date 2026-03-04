"""FastAPI backend — thin HTTP layer over the Customer Success Agent."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents import RunContextWrapper

from agent import get_correlation_id, set_correlation_id
from agent.cache import get_job, set_job
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


class JobAccepted(BaseModel):
    job_id: str
    status: str = "processing"
    retry_after: int = 5


class JobStatus(BaseModel):
    job_id: str
    status: str
    response: str | None = None
    error: str | None = None
    retry_after: int | None = None


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
# Background task helpers
# ---------------------------------------------------------------------------


async def _process_chat(job_id: str, message: str, ctx) -> None:
    """Run the agent in the background and store the result as a job."""
    set_correlation_id(job_id)
    logger.info("Job %s started — background processing", job_id)
    try:
        response = await run_agent(ctx, message)
        await set_job(ctx.redis_client, job_id, {"status": "completed", "response": response})
        logger.info("Job %s completed — response stored", job_id)
    except Exception as exc:
        logger.exception("Job %s failed — %s", job_id, exc)
        await set_job(ctx.redis_client, job_id, {
            "status": "failed",
            "response": None,
            "error": "An error occurred while processing your request. Please try again.",
        })


async def _process_webhook(job_id: str, channel: str, from_address: str, body: str, ctx) -> None:
    """Run the agent in the background for a webhook request."""
    set_correlation_id(job_id)
    logger.info("Job %s started — %s webhook processing", job_id, channel)
    try:
        message = f"[Customer: {from_address}, Channel: {channel}] {body}"
        response = await run_agent(ctx, message)
        await set_job(ctx.redis_client, job_id, {"status": "completed", "response": response})
        logger.info("Job %s completed — %s response stored", job_id, channel)
    except Exception as exc:
        logger.exception("Job %s failed — %s — %s", job_id, channel, exc)
        await set_job(ctx.redis_client, job_id, {
            "status": "failed",
            "response": None,
            "error": "An error occurred while processing your request. Please try again.",
        })


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(
    req: ChatRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    sync: bool = Query(False),
):
    cid = set_correlation_id()
    logger.info("Chat request — email=%s channel=%s", req.email, req.channel)

    ctx = request.app.state.agent_ctx
    message = f"[Customer: {req.email}, Channel: {req.channel}] {req.message}"

    # Sync mode: explicit ?sync=true OR graceful fallback when Redis is unavailable
    if sync or ctx.redis_client is None:
        if ctx.redis_client is None and not sync:
            logger.warning("Redis unavailable — falling back to sync mode")
        response = await run_agent(ctx, message)
        return ChatResponse(response=response, correlation_id=cid)

    # Async mode (default)
    await set_job(ctx.redis_client, cid, {"status": "processing"})
    background_tasks.add_task(_process_chat, cid, message, ctx)
    return JSONResponse(status_code=202, content=JobAccepted(job_id=cid).model_dump())


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def job_status(job_id: str, request: Request):
    ctx = request.app.state.agent_ctx
    data = await get_job(ctx.redis_client, job_id)
    if data is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})

    retry = 5 if data.get("status") == "processing" else None
    return JobStatus(
        job_id=job_id,
        status=data["status"],
        response=data.get("response"),
        error=data.get("error"),
        retry_after=retry,
    )


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


@app.post("/api/webhooks/gmail")
async def webhook_gmail(payload: WebhookPayload, request: Request, background_tasks: BackgroundTasks):
    cid = set_correlation_id()
    logger.info("Gmail webhook — from=%s", payload.from_address)

    ctx = request.app.state.agent_ctx

    if ctx.redis_client is None:
        logger.warning("Redis unavailable — falling back to sync mode (gmail)")
        message = f"[Customer: {payload.from_address}, Channel: gmail] {payload.body}"
        response = await run_agent(ctx, message)
        return ChatResponse(response=response, correlation_id=cid)

    await set_job(ctx.redis_client, cid, {"status": "processing"})
    background_tasks.add_task(_process_webhook, cid, "gmail", payload.from_address, payload.body, ctx)
    return JSONResponse(status_code=202, content=JobAccepted(job_id=cid).model_dump())


@app.post("/api/webhooks/whatsapp")
async def webhook_whatsapp(payload: WebhookPayload, request: Request, background_tasks: BackgroundTasks):
    cid = set_correlation_id()
    logger.info("WhatsApp webhook — from=%s", payload.from_address)

    ctx = request.app.state.agent_ctx

    if ctx.redis_client is None:
        logger.warning("Redis unavailable — falling back to sync mode (whatsapp)")
        message = f"[Customer: {payload.from_address}, Channel: whatsapp] {payload.body}"
        response = await run_agent(ctx, message)
        return ChatResponse(response=response, correlation_id=cid)

    await set_job(ctx.redis_client, cid, {"status": "processing"})
    background_tasks.add_task(_process_webhook, cid, "whatsapp", payload.from_address, payload.body, ctx)
    return JSONResponse(status_code=202, content=JobAccepted(job_id=cid).model_dump())
