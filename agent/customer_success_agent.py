"""Customer Success Agent — OpenAI Agents SDK definition and runner."""

from __future__ import annotations

import os

from agents import Agent, Runner

from agent.context import AgentContext
from agent.prompts import SYSTEM_PROMPT
from agent.tools import ALL_TOOLS

_DEFAULT_MODEL = "gpt-4o"

customer_success_agent = Agent[AgentContext](
    name="Customer Success Agent",
    instructions=SYSTEM_PROMPT,
    tools=ALL_TOOLS,
    model=os.environ.get("OPENAI_MODEL", _DEFAULT_MODEL),
)


async def run_agent(
    context: AgentContext,
    message: str,
) -> str:
    """Run the Customer Success Agent on a single message.

    Parameters
    ----------
    context:
        Shared agent context (DB pool + OpenAI client).
    message:
        The customer's inbound message text.

    Returns
    -------
    str
        The agent's final textual output.
    """
    result = await Runner.run(
        starting_agent=customer_success_agent,
        input=message,
        context=context,
    )
    return result.final_output
