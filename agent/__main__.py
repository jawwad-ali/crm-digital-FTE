"""CLI entry point for smoke-testing the Customer Success Agent.

Usage:
    python -m agent "How do I reset my password?" --email alice@example.com
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from dotenv import load_dotenv

from agent import set_correlation_id
from agent.context import build_context
from agent.customer_success_agent import run_agent
from agent.tools.customer import find_or_create_customer

logger = logging.getLogger(__name__)


async def main(message: str, email: str) -> None:
    load_dotenv()

    cid = set_correlation_id()
    logger.info("Starting agent — correlation_id=%s", cid)

    ctx = await build_context()

    try:
        # Pre-identify the customer so the agent has context
        from agents import RunContextWrapper

        wrapper = RunContextWrapper(context=ctx)
        await find_or_create_customer.on_invoke_tool(
            wrapper,
            '{"identifier_type": "email", "identifier_value": "' + email + '"}',
        )

        # Run the agent
        response = await run_agent(ctx, f"[Customer: {email}] {message}")
        print("\n--- Agent Response ---")
        print(response)
    finally:
        await ctx.db_pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke-test the Customer Success Agent")
    parser.add_argument("message", help="Customer message to send")
    parser.add_argument("--email", default="alice@example.com", help="Customer email")
    args = parser.parse_args()

    asyncio.run(main(args.message, args.email))
