# Feature Specification: Customer Success Agent

**Feature Branch**: `001-customer-success-agent`
**Created**: 2026-02-22
**Status**: Draft
**Input**: User description: "Build the core Customer Success AI agent using OpenAI Agents SDK backed by a complete PostgreSQL schema. The agent autonomously decides which @function_tool functions to call. Tools cover customer management, ticket lifecycle, knowledge base semantic search, conversation persistence, escalation, response delivery, and metrics logging. Each tool is an async Python function running PostgreSQL queries via asyncpg."

## Clarifications

### Session 2026-02-22

- Q: What is the semantic search similarity threshold for knowledge base matches? → A: 0.7 (cosine similarity). Below this, the agent treats it as "no match" and escalates.
- Q: Who computes the sentiment score stored with each message? → A: The agent (LLM) estimates sentiment inline during its reasoning and passes the score (0.0–1.0) to `save_message`. No separate sentiment tool or service needed.
- Q: How does a second channel identifier get linked to an existing customer? → A: Agent-prompted. The agent asks the customer for a known identifier (e.g., "What email is your account under?") and calls `find_or_create_customer` with both identifiers to link them. No automatic or admin-only merging.
- Q: What are the valid ticket state transitions? → A: Forward-only. open → in_progress → resolved; any state → escalated. No reopening — if a resolved ticket needs follow-up, the agent creates a new ticket referencing the old one.
- Q: When is a new conversation created vs continuing an existing one? → A: Ticket-bound. One conversation per ticket. New ticket = new conversation. This gives 1:1 ticket-conversation traceability.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Web Form Customer Gets an Accurate Answer (Priority: P1)

A customer submits a product question through the web form. The agent receives the message, identifies or creates the customer, creates a ticket, searches the knowledge base for a relevant answer, saves the conversation, sends the response, and logs metrics — all autonomously without hardcoded orchestration.

**Why this priority**: This is the end-to-end happy path that proves the agent works. If this story passes, the core system is viable.

**Independent Test**: Submit a product question that matches a seeded knowledge base article. Verify the customer is created, a ticket is opened, the correct answer is returned, the ticket is resolved, and a metric is logged.

**Acceptance Scenarios**:

1. **Given** no existing customer, **When** a web form message arrives with email "alice@example.com" asking "How do I reset my password?", **Then** the agent creates the customer, creates a ticket (channel=web, status=open), searches the knowledge base, finds the password reset article, sends an accurate response, updates the ticket to resolved, and logs a metric.
2. **Given** a returning customer with prior tickets, **When** they submit a new question, **Then** the agent retrieves their history for context before responding.
3. **Given** the knowledge base contains a matching article with cosine similarity >= 0.7, **When** the agent searches, **Then** the response incorporates the article content without fabricating information.

---

### User Story 2 - Agent Escalates When It Cannot Help (Priority: P1)

A customer submits a request that is outside the agent's scope (refund request, legal question, or very negative sentiment). The agent must recognise this, escalate to a human, and inform the customer — rather than attempting an answer.

**Why this priority**: Escalation safety is a non-negotiable guardrail. An agent that fabricates answers or mishandles angry customers is worse than no agent.

**Independent Test**: Submit a refund request. Verify the ticket is created, marked as escalated with a reason, the human queue is notified, and the customer receives an acknowledgement.

**Acceptance Scenarios**:

1. **Given** a customer sends "I want a full refund, this product is terrible", **When** the agent analyses the message, **Then** it creates a ticket, detects the refund request as out-of-scope, calls `escalate_to_human` with reason "refund request — out of scope", and sends a response acknowledging the escalation.
2. **Given** a customer's sentiment score is below 0.3, **When** the agent evaluates the interaction, **Then** it escalates regardless of the question content.
3. **Given** the knowledge base returns no results with cosine similarity >= 0.7, **When** the agent cannot answer, **Then** it escalates with reason "no knowledge base match" rather than guessing.

---

### User Story 3 - Cross-Channel Customer Continuity (Priority: P2)

A customer contacts support via web form using their email, then later messages via WhatsApp using their phone number. The agent must recognise these as the same customer and have access to the full conversation history from both channels.

**Why this priority**: Cross-channel identity is a key differentiator for the Digital FTE. Without it, customers repeat themselves across channels.

**Independent Test**: Create a customer via email on web, link a phone number via WhatsApp, then query history — both channel conversations should appear under one customer.

**Acceptance Scenarios**:

1. **Given** customer "alice@example.com" has a resolved web ticket, **When** a WhatsApp message arrives from "+15551234567" and is linked to the same customer, **Then** `get_customer_history` returns conversations from both web and WhatsApp.
2. **Given** a WhatsApp user provides their email when prompted by the agent, **When** `find_or_create_customer` is called with both phone and email, **Then** the phone identifier is linked to the existing customer record found by email.
3. **Given** a customer has 3 conversations across 2 channels, **When** the agent handles a new message, **Then** it loads recent history for context continuity in its response.

---

### User Story 4 - Knowledge Base Powers Agent Answers (Priority: P2)

The knowledge base is pre-seeded with product documentation. The agent uses semantic search to find the most relevant articles and incorporates them into responses. Articles that don't match are excluded.

**Why this priority**: Without a populated, searchable knowledge base the agent has nothing to answer from and must escalate every question.

**Independent Test**: Seed 15+ articles covering product features, how-tos, and troubleshooting. Query with 10 different questions and verify the top result is relevant at least 85% of the time.

**Acceptance Scenarios**:

1. **Given** 15+ seeded knowledge base articles with embeddings, **When** the agent searches for "how do I change my notification settings", **Then** the notification settings article appears in the top 3 results.
2. **Given** an article about billing exists, **When** a customer asks about billing, **Then** the agent's response references the article content accurately.
3. **Given** no article matches the query (all cosine similarities < 0.7), **When** the agent searches, **Then** it receives an empty result set and proceeds to escalate.

---

### User Story 5 - Agent Logs Metrics for Every Interaction (Priority: P3)

Every interaction the agent handles must produce a metrics entry recording response time, customer sentiment, channel, and resolution type (auto-resolved, escalated). These metrics enable reporting dashboards and performance monitoring.

**Why this priority**: Metrics are essential for measuring the agent's ROI and identifying improvement areas, but the agent functions without them.

**Independent Test**: Process 5 interactions, then query metrics by channel and verify all 5 entries exist with correct data.

**Acceptance Scenarios**:

1. **Given** the agent resolves a web form question in 1.8 seconds, **When** the interaction completes, **Then** a metric row is logged with response_time=1.8, sentiment=0.75, channel="web", resolution="auto_resolved".
2. **Given** the agent escalates a ticket, **When** the interaction completes, **Then** a metric row is logged with resolution="escalated" and the escalation reason.
3. **Given** 100 metric entries exist, **When** metrics are queried grouped by channel, **Then** aggregated counts and averages are returned.

---

### Edge Cases

- What happens when two customers share the same email? The system enforces unique identifiers per (type, value) — duplicate insertion is rejected.
- What happens when a message arrives for a resolved conversation? A new ticket (and its corresponding conversation) is created under the same customer.
- What happens when the agent's LLM call fails mid-interaction? The tool must catch the error, log it, create a ticket marked as escalated with reason "system error", and return a fallback apology response.
- What happens when the database connection pool is exhausted? Tools must raise a clear error that triggers escalation rather than hanging indefinitely.
- What happens when the agent calls tools in an unexpected order (e.g., send_response before create_ticket)? The guardrail "always create ticket before responding" is enforced in the system prompt; if violated, the response tool should verify a ticket exists and create one if missing.
- What happens when embedding generation fails for a knowledge base article? The article is stored but excluded from semantic search results.
- What happens when a customer's sentiment fluctuates across messages? The agent evaluates sentiment per-message and checks the latest sentiment before closing a ticket.

## Requirements *(mandatory)*

### Functional Requirements

**Database Schema**

- **FR-001**: System MUST provide a `customers` table storing unique customer records with created/updated timestamps.
- **FR-002**: System MUST provide a `customer_identifiers` table linking emails and phone numbers to customers, with a unique constraint on (identifier_type, identifier_value).
- **FR-003**: System MUST provide a `conversations` table grouping messages under a customer with channel and status. Conversations are ticket-bound: one conversation per ticket (1:1 relationship). A new ticket always creates a new conversation.
- **FR-004**: System MUST provide a `messages` table storing each message with direction, channel, content, sentiment score, and timestamps.
- **FR-005**: System MUST provide a `tickets` table with status lifecycle (open, in_progress, resolved, escalated), category, priority, channel, and resolution notes. Valid transitions are forward-only: open → in_progress → resolved; any state → escalated. No reopening — a new ticket is created instead.
- **FR-006**: System MUST provide a `knowledge_base` table with title, content, category, and a vector embedding column for semantic search.
- **FR-007**: System MUST enable the pgvector extension and create vector indexes for cosine similarity search.
- **FR-008**: System MUST provide a `channel_configs` table with per-channel settings (response style, max length, enabled flag).
- **FR-009**: System MUST provide an `agent_metrics` table logging response time, sentiment, channel, resolution type, and timestamp.
- **FR-010**: System MUST include seed data with 15+ knowledge base articles containing pre-computed embeddings.
- **FR-011**: System MUST use versioned SQL migration files for schema changes.
- **FR-012**: System MUST enforce referential integrity via foreign keys between all related tables.

**Agent Tools**

- **FR-013**: System MUST provide `find_or_create_customer` — looks up customer by email/phone, creates if new. Cross-channel identity linking is agent-prompted: the agent asks the customer for a known identifier and passes both to this tool to merge.
- **FR-014**: System MUST provide `get_customer_history` — fetches all past conversations across all channels for a customer.
- **FR-015**: System MUST provide `create_ticket` — logs a new interaction with channel, category, and priority.
- **FR-016**: System MUST provide `update_ticket` — changes ticket status and adds resolution notes.
- **FR-017**: System MUST provide `get_ticket` — fetches ticket details and conversation thread.
- **FR-018**: System MUST provide `search_knowledge_base` — performs semantic search using cosine similarity on product docs; results with similarity < 0.7 MUST be excluded.
- **FR-019**: System MUST provide `save_message` — stores each message with channel metadata and sentiment score (0.0–1.0, computed inline by the agent LLM).
- **FR-020**: System MUST provide `get_conversation_messages` — loads conversation history for context continuity.
- **FR-021**: System MUST provide `escalate_to_human` — marks ticket as escalated, records reason, notifies human queue.
- **FR-022**: System MUST provide `send_response` — formats and sends reply through the correct channel.
- **FR-023**: System MUST provide `log_metric` — records response time, sentiment, channel, and resolution type.
- **FR-024**: Every tool MUST be an async Python function decorated with `@function_tool` and accept a Pydantic input model.
- **FR-025**: Every tool MUST run its database queries via an async driver.
- **FR-026**: Every tool MUST include error handling with structured logging and graceful fallback.

**Agent Behavior**

- **FR-027**: The agent MUST autonomously decide which tools to call and in what order — no hardcoded control flow.
- **FR-028**: The agent MUST always create a ticket before sending a response.
- **FR-029**: The agent MUST always check sentiment before closing a ticket (sentiment < 0.3 triggers escalation).
- **FR-030**: The agent MUST never discuss competitor products.
- **FR-031**: The agent MUST never promise features not present in the knowledge base.
- **FR-032**: The agent MUST escalate when the knowledge base returns no relevant match rather than fabricating an answer.
- **FR-033**: The agent MUST use channel-appropriate tone and length in responses (formal for email, concise for WhatsApp, semi-formal for web).

### Key Entities

- **Customer**: A unique person interacting with the system. Has one or more identifiers. Central entity linked to conversations, tickets, and metrics.
- **Customer Identifier**: An email or phone number linked to a customer. Enables cross-channel identity resolution.
- **Conversation**: A thread of messages between a customer and the agent. Belongs to one customer, references one channel. 1:1 with a ticket — every ticket has exactly one conversation.
- **Message**: A single inbound or outbound communication. Carries content, sentiment, channel metadata, and direction.
- **Ticket**: A unit of customer service work. Forward-only status lifecycle: open → in_progress → resolved; any → escalated. Has category, priority, and resolution notes. Follow-ups on resolved tickets create a new ticket.
- **Knowledge Base Article**: A product documentation entry with vector embedding for semantic similarity search.
- **Channel Config**: Runtime configuration for a channel (web, gmail, whatsapp) — response style, max length, enabled flag.
- **Agent Metric**: A performance data point per interaction — response time, sentiment, channel, resolution type.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The agent resolves a standard product question end-to-end (customer creation through response delivery) without human intervention.
- **SC-002**: A customer is identified across 3 channels via linked identifiers, resolving to one record 100% of the time.
- **SC-003**: Semantic search returns the most relevant knowledge base article in the top 3 results for at least 85% of test queries.
- **SC-004**: The agent escalates 100% of out-of-scope requests (refunds, legal, low sentiment) without attempting an answer.
- **SC-005**: All 11 agent tools execute successfully with proper error handling — no unhandled exceptions.
- **SC-006**: Response time from message receipt to agent reply is under 3 seconds for 95% of interactions.
- **SC-007**: Every interaction produces a metric entry with all required fields populated.
- **SC-008**: The agent never fabricates information — responses are traceable to knowledge base articles or escalation.
- **SC-009**: All 8 database tables can be created from migration files on a fresh database in a single run.
- **SC-010**: Knowledge base is pre-seeded with at least 15 product documentation entries ready for semantic search.

### Assumptions

- Embedding dimension is 1536 (OpenAI text-embedding-3-small). Adjustable at migration time if a different model is used.
- Neon PostgreSQL 16 supports pgvector (confirmed by Neon documentation).
- Seed data uses a fictional SaaS product consistent with the hackathon spec context files.
- The `send_response` tool will initially format responses for the web channel only; Gmail and WhatsApp channel delivery will be wired in a later feature (MCP channel integrations).
- The human escalation queue is a database-backed queue (a ticket with status "escalated") — no external notification system is required for this feature.
