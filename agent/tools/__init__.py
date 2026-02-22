"""Agent tools registry — exports all @function_tool instances for agent registration."""

from agent.tools.conversation import get_conversation_messages, save_message
from agent.tools.customer import find_or_create_customer, get_customer_history
from agent.tools.escalation import escalate_to_human
from agent.tools.knowledge import search_knowledge_base
from agent.tools.response import send_response
from agent.tools.ticket import create_ticket, get_ticket, update_ticket

# US1 tools — core happy-path toolset
US1_TOOLS: list = [
    find_or_create_customer,
    get_customer_history,
    create_ticket,
    update_ticket,
    get_ticket,
    search_knowledge_base,
    save_message,
    get_conversation_messages,
    send_response,
]

# US2 tools — escalation
US2_TOOLS: list = [
    escalate_to_human,
]

# All tools — extended as user stories are added
ALL_TOOLS: list = list(US1_TOOLS) + US2_TOOLS
