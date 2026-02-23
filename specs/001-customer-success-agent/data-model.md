# Data Model: Customer Success Agent

**Feature Branch**: `001-customer-success-agent`
**Date**: 2026-02-22

## Entity Relationship Overview

```
customers 1──* customer_identifiers
customers 1──* tickets
tickets   1──1 conversations
conversations 1──* messages
customers 1──* agent_metrics
channel_configs (standalone)
knowledge_base (standalone)
```

## Entities

### customers

| Column     | Type        | Constraints              | Description                   |
|------------|-------------|--------------------------|-------------------------------|
| id         | UUID        | PK, DEFAULT gen_random_uuid() | Unique customer identifier |
| name       | VARCHAR(255)| NULLABLE                 | Customer display name (if known) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now()  | Record creation time          |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now()  | Last modification time        |

### customer_identifiers

| Column          | Type        | Constraints                              | Description                       |
|-----------------|-------------|------------------------------------------|-----------------------------------|
| id              | UUID        | PK, DEFAULT gen_random_uuid()            | Row identifier                    |
| customer_id     | UUID        | FK → customers.id, NOT NULL              | Owning customer                   |
| identifier_type | VARCHAR(20) | NOT NULL, CHECK IN ('email', 'phone')    | Type of identifier                |
| identifier_value| VARCHAR(255)| NOT NULL                                 | The email address or phone number |
| channel         | VARCHAR(20) | NOT NULL, CHECK IN ('web', 'gmail', 'whatsapp') | Channel this identifier came from |
| created_at      | TIMESTAMPTZ | NOT NULL, DEFAULT now()                  | When identifier was linked        |

**Unique constraint**: `(identifier_type, identifier_value)` — one email/phone maps to exactly one customer.

### tickets

| Column          | Type        | Constraints                                    | Description                       |
|-----------------|-------------|------------------------------------------------|-----------------------------------|
| id              | UUID        | PK, DEFAULT gen_random_uuid()                  | Ticket identifier                 |
| customer_id     | UUID        | FK → customers.id, NOT NULL                    | Owning customer                   |
| channel         | VARCHAR(20) | NOT NULL, CHECK IN ('web', 'gmail', 'whatsapp')| Originating channel               |
| category        | VARCHAR(50) | NOT NULL                                       | e.g., how-to, bug-report, feedback|
| priority        | VARCHAR(20) | NOT NULL, CHECK IN ('low', 'medium', 'high', 'urgent') | Ticket priority          |
| status          | VARCHAR(20) | NOT NULL, DEFAULT 'open', CHECK IN ('open', 'in_progress', 'resolved', 'escalated') | Current status |
| escalation_reason| TEXT       | NULLABLE                                       | Reason if escalated               |
| resolution_notes| TEXT        | NULLABLE                                       | Notes when resolved               |
| parent_ticket_id| UUID        | FK → tickets.id, NULLABLE                      | References prior ticket for follow-ups |
| created_at      | TIMESTAMPTZ | NOT NULL, DEFAULT now()                        | Ticket creation time              |
| updated_at      | TIMESTAMPTZ | NOT NULL, DEFAULT now()                        | Last status change                |

**State transitions** (forward-only):
- `open` → `in_progress` → `resolved`
- Any state → `escalated`
- No reopening; follow-ups create a new ticket with `parent_ticket_id` referencing the old one.

### conversations

| Column      | Type        | Constraints                              | Description                    |
|-------------|-------------|------------------------------------------|--------------------------------|
| id          | UUID        | PK, DEFAULT gen_random_uuid()            | Conversation identifier        |
| ticket_id   | UUID        | FK → tickets.id, NOT NULL, UNIQUE        | 1:1 with ticket                |
| customer_id | UUID        | FK → customers.id, NOT NULL              | Owning customer                |
| channel     | VARCHAR(20) | NOT NULL, CHECK IN ('web', 'gmail', 'whatsapp') | Channel of this conversation |
| created_at  | TIMESTAMPTZ | NOT NULL, DEFAULT now()                  | Conversation start time        |

**Relationship**: 1:1 with tickets (UNIQUE constraint on `ticket_id`). Every ticket creates exactly one conversation.

### messages

| Column          | Type        | Constraints                              | Description                      |
|-----------------|-------------|------------------------------------------|----------------------------------|
| id              | UUID        | PK, DEFAULT gen_random_uuid()            | Message identifier               |
| conversation_id | UUID        | FK → conversations.id, NOT NULL          | Parent conversation              |
| direction       | VARCHAR(10) | NOT NULL, CHECK IN ('inbound', 'outbound')| Message direction               |
| channel         | VARCHAR(20) | NOT NULL, CHECK IN ('web', 'gmail', 'whatsapp') | Channel metadata          |
| content         | TEXT        | NOT NULL                                 | Message body                     |
| sentiment       | FLOAT       | NULLABLE, CHECK (sentiment >= 0 AND sentiment <= 1) | Agent-estimated sentiment (0.0–1.0) |
| created_at      | TIMESTAMPTZ | NOT NULL, DEFAULT now()                  | Message timestamp                |

### knowledge_base

| Column    | Type          | Constraints                    | Description                        |
|-----------|---------------|--------------------------------|------------------------------------|
| id        | UUID          | PK, DEFAULT gen_random_uuid()  | Article identifier                 |
| title     | VARCHAR(255)  | NOT NULL                       | Article title                      |
| content   | TEXT          | NOT NULL                       | Full article text                  |
| category  | VARCHAR(50)   | NOT NULL                       | e.g., getting-started, billing, troubleshooting |
| embedding | VECTOR(1536)  | NULLABLE                       | OpenAI text-embedding-3-small vector |
| created_at| TIMESTAMPTZ   | NOT NULL, DEFAULT now()        | Article creation time              |
| updated_at| TIMESTAMPTZ   | NOT NULL, DEFAULT now()        | Last edit time                     |

**Index**: IVFFlat on `embedding` column using `vector_cosine_ops` for cosine similarity search.
**Note**: Articles with NULL embedding are stored but excluded from semantic search.

### channel_configs

| Column         | Type        | Constraints                              | Description                     |
|----------------|-------------|------------------------------------------|---------------------------------|
| id             | UUID        | PK, DEFAULT gen_random_uuid()            | Config row identifier           |
| channel        | VARCHAR(20) | NOT NULL, UNIQUE, CHECK IN ('web', 'gmail', 'whatsapp') | Channel name     |
| response_style | VARCHAR(50) | NOT NULL                                 | e.g., formal, conversational, semi-formal |
| max_length     | INTEGER     | NOT NULL                                 | Max response length (chars)     |
| enabled        | BOOLEAN     | NOT NULL, DEFAULT true                   | Channel enabled flag            |
| created_at     | TIMESTAMPTZ | NOT NULL, DEFAULT now()                  | Record creation time            |
| updated_at     | TIMESTAMPTZ | NOT NULL, DEFAULT now()                  | Last modification time          |

**Seed values**:
- web: response_style="semi-formal", max_length=1500, enabled=true
- gmail: response_style="formal", max_length=2500, enabled=true
- whatsapp: response_style="conversational", max_length=800, enabled=true

### agent_metrics

| Column          | Type        | Constraints                    | Description                      |
|-----------------|-------------|--------------------------------|----------------------------------|
| id              | UUID        | PK, DEFAULT gen_random_uuid()  | Metric row identifier            |
| customer_id     | UUID        | FK → customers.id, NULLABLE    | Customer (if identified)         |
| ticket_id       | UUID        | FK → tickets.id, NULLABLE      | Related ticket                   |
| channel         | VARCHAR(20) | NOT NULL                       | Channel of interaction           |
| response_time_ms| INTEGER     | NOT NULL                       | Agent response time in milliseconds |
| sentiment       | FLOAT       | NULLABLE                       | Final sentiment score            |
| resolution_type | VARCHAR(30) | NOT NULL, CHECK IN ('auto_resolved', 'escalated', 'error') | How it ended |
| escalation_reason| TEXT       | NULLABLE                       | Reason if escalated              |
| created_at      | TIMESTAMPTZ | NOT NULL, DEFAULT now()        | Metric timestamp                 |

## Indexes

| Table                 | Index                                                    | Purpose                      |
|-----------------------|----------------------------------------------------------|------------------------------|
| customer_identifiers  | UNIQUE (identifier_type, identifier_value)               | Fast customer lookup         |
| customer_identifiers  | (customer_id)                                            | FK lookup                    |
| tickets               | (customer_id, created_at DESC)                           | Customer ticket history      |
| tickets               | (status) WHERE status IN ('open', 'in_progress')         | Active ticket queries        |
| conversations         | UNIQUE (ticket_id)                                       | 1:1 enforcement              |
| conversations         | (customer_id)                                            | Customer conversation lookup |
| messages              | (conversation_id, created_at)                            | Chronological message fetch  |
| knowledge_base        | IVFFlat (embedding vector_cosine_ops) WITH (lists = 10)  | Semantic search              |
| agent_metrics         | (channel, created_at)                                    | Channel metrics aggregation  |
