# Tool Contracts: Customer Success Agent

**Feature Branch**: `001-customer-success-agent`
**Date**: 2026-02-22

Each tool below is an `@function_tool` async function. Parameters use Pydantic types.
The first parameter `ctx: RunContextWrapper[AgentContext]` is injected by the SDK and
is NOT visible to the LLM.

---

## Customer Management

### find_or_create_customer

```
Input:
  identifier_type: str   — "email" | "phone"
  identifier_value: str  — the email address or phone number
  name: str | None       — optional customer name
  link_to_identifier_value: str | None — if provided, link this new identifier
                                         to the customer found by this value

Output (JSON string):
  customer_id: str       — UUID of the found or created customer
  is_new: bool           — true if customer was just created
  identifiers: list      — all identifiers linked to this customer

Errors:
  - identifier_value empty → return error message
  - link_to_identifier_value not found → return "no customer found to link"

DB operations:
  1. SELECT customer_id FROM customer_identifiers WHERE identifier_type=$1 AND identifier_value=$2
  2. If found → return customer
  3. If link_to_identifier_value provided → find that customer, add new identifier
  4. If not found and no link → INSERT customers, INSERT customer_identifiers
```

### get_customer_history

```
Input:
  customer_id: str       — UUID of the customer

Output (JSON string):
  customer: object       — customer record with name, created_at
  identifiers: list      — all linked identifiers
  conversations: list    — recent conversations (last 10) with channel, created_at, message_count
  tickets: list          — recent tickets (last 10) with status, category, channel

Errors:
  - customer_id not found → return "customer not found"

DB operations:
  1. SELECT * FROM customers WHERE id=$1
  2. SELECT * FROM customer_identifiers WHERE customer_id=$1
  3. SELECT * FROM conversations WHERE customer_id=$1 ORDER BY created_at DESC LIMIT 10
  4. SELECT * FROM tickets WHERE customer_id=$1 ORDER BY created_at DESC LIMIT 10
```

---

## Ticket Lifecycle

### create_ticket

```
Input:
  customer_id: str       — UUID of the customer
  channel: str           — "web" | "gmail" | "whatsapp"
  category: str          — e.g., "how-to", "bug-report", "feedback", "billing", "general"
  priority: str          — "low" | "medium" | "high" | "urgent"

Output (JSON string):
  ticket_id: str         — UUID of the new ticket
  conversation_id: str   — UUID of the auto-created conversation
  status: str            — "open"

Errors:
  - customer_id not found → return error

DB operations (single transaction):
  1. INSERT INTO tickets (customer_id, channel, category, priority, status)
  2. INSERT INTO conversations (ticket_id, customer_id, channel)
  3. RETURN both IDs
```

### update_ticket

```
Input:
  ticket_id: str         — UUID of the ticket
  status: str            — "in_progress" | "resolved" | "escalated"
  resolution_notes: str | None — notes when resolving
  escalation_reason: str | None — reason when escalating

Output (JSON string):
  ticket_id: str
  old_status: str
  new_status: str
  updated_at: str

Errors:
  - ticket not found → return error
  - invalid transition (e.g., resolved → open) → return "invalid status transition"

DB operations:
  1. SELECT status FROM tickets WHERE id=$1
  2. Validate transition: open→in_progress, in_progress→resolved, any→escalated
  3. UPDATE tickets SET status=$2, resolution_notes=$3, escalation_reason=$4, updated_at=now()
```

### get_ticket

```
Input:
  ticket_id: str         — UUID of the ticket

Output (JSON string):
  ticket: object         — full ticket record
  conversation: object   — linked conversation
  messages: list         — all messages in the conversation (chronological)

Errors:
  - ticket not found → return error

DB operations:
  1. SELECT * FROM tickets WHERE id=$1
  2. SELECT * FROM conversations WHERE ticket_id=$1
  3. SELECT * FROM messages WHERE conversation_id=<conv_id> ORDER BY created_at
```

---

## Knowledge Base

### search_knowledge_base

```
Input:
  query: str             — the user's question (will be embedded)
  top_k: int = 3         — number of results to return (default 3)

Output (JSON string):
  results: list          — top_k articles with fields:
    - id: str
    - title: str
    - content: str
    - category: str
    - similarity: float
  If no results with similarity >= 0.7 → empty list

Errors:
  - embedding generation fails → return "knowledge base search unavailable"

DB operations:
  1. Generate embedding for query via OpenAI API
  2. SELECT id, title, content, category, 1 - (embedding <=> $1) AS similarity
     FROM knowledge_base
     WHERE embedding IS NOT NULL AND 1 - (embedding <=> $1) >= 0.7
     ORDER BY embedding <=> $1
     LIMIT $2
```

---

## Conversation

### save_message

```
Input:
  conversation_id: str   — UUID of the conversation
  direction: str         — "inbound" | "outbound"
  channel: str           — "web" | "gmail" | "whatsapp"
  content: str           — message text
  sentiment: float | None — 0.0 to 1.0 (agent-estimated)

Output (JSON string):
  message_id: str        — UUID of the saved message
  created_at: str

Errors:
  - conversation not found → return error
  - sentiment out of range → clamp to [0.0, 1.0]

DB operations:
  1. INSERT INTO messages (conversation_id, direction, channel, content, sentiment)
```

### get_conversation_messages

```
Input:
  conversation_id: str   — UUID of the conversation

Output (JSON string):
  messages: list         — all messages in chronological order with:
    - id, direction, channel, content, sentiment, created_at

Errors:
  - conversation not found → return error

DB operations:
  1. SELECT * FROM messages WHERE conversation_id=$1 ORDER BY created_at
```

---

## Escalation

### escalate_to_human

```
Input:
  ticket_id: str         — UUID of the ticket to escalate
  reason: str            — why escalation is needed

Output (JSON string):
  ticket_id: str
  status: str            — "escalated"
  reason: str
  escalated_at: str

Errors:
  - ticket not found → return error

DB operations:
  1. UPDATE tickets SET status='escalated', escalation_reason=$2, updated_at=now()
     WHERE id=$1
```

---

## Response

### send_response

```
Input:
  conversation_id: str   — UUID of the conversation
  channel: str           — "web" | "gmail" | "whatsapp"
  content: str           — response text to send
  ticket_id: str | None  — ticket ID for safety check

Output (JSON string):
  message_id: str        — UUID of the saved outbound message
  channel: str
  delivered: bool        — true if sent (web always true; gmail/whatsapp depend on MCP)

Pre-conditions:
  - If ticket_id is None, look up the ticket via conversation → ticket
  - If no ticket exists for this conversation, create one (safety net for guardrail violation)

DB operations:
  1. Verify ticket exists for conversation
  2. Fetch channel_configs for response formatting (max_length, response_style)
  3. Truncate content to max_length if needed
  4. INSERT INTO messages (conversation_id, direction='outbound', channel, content)
  5. For web: return message (FastAPI will deliver)
  6. For gmail/whatsapp: delegate to MCP tools (future feature — return delivered=false for now)
```

---

## Metrics

### log_metric

```
Input:
  customer_id: str | None — customer UUID (if identified)
  ticket_id: str | None   — ticket UUID (if exists)
  channel: str            — "web" | "gmail" | "whatsapp"
  response_time_ms: int   — agent processing time in milliseconds
  sentiment: float | None — final sentiment score
  resolution_type: str    — "auto_resolved" | "escalated" | "error"
  escalation_reason: str | None — reason if escalated

Output (JSON string):
  metric_id: str          — UUID of the logged metric
  created_at: str

Errors:
  - Never fails fatally — log errors are best-effort

DB operations:
  1. INSERT INTO agent_metrics (customer_id, ticket_id, channel, response_time_ms,
     sentiment, resolution_type, escalation_reason)
```
