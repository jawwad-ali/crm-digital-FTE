-- 001_initial_schema.sql
-- Customer Success Agent — initial database schema
-- Requires PostgreSQL 16+ with pgvector extension

BEGIN;

-- Enable pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 1. customers
-- ============================================================
CREATE TABLE customers (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 2. customer_identifiers
-- ============================================================
CREATE TABLE customer_identifiers (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id      UUID        NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type  VARCHAR(20) NOT NULL CHECK (identifier_type IN ('email', 'phone')),
    identifier_value VARCHAR(255) NOT NULL,
    channel          VARCHAR(20) NOT NULL CHECK (channel IN ('web', 'gmail', 'whatsapp')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (identifier_type, identifier_value)
);

CREATE INDEX idx_customer_identifiers_customer_id
    ON customer_identifiers (customer_id);

-- ============================================================
-- 3. tickets
-- ============================================================
CREATE TABLE tickets (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id       UUID        NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel           VARCHAR(20) NOT NULL CHECK (channel IN ('web', 'gmail', 'whatsapp')),
    category          VARCHAR(50) NOT NULL,
    priority          VARCHAR(20) NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status            VARCHAR(20) NOT NULL DEFAULT 'open'
                                  CHECK (status IN ('open', 'in_progress', 'resolved', 'escalated')),
    escalation_reason TEXT,
    resolution_notes  TEXT,
    parent_ticket_id  UUID        REFERENCES tickets(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tickets_customer_history
    ON tickets (customer_id, created_at DESC);

CREATE INDEX idx_tickets_active
    ON tickets (status)
    WHERE status IN ('open', 'in_progress');

-- ============================================================
-- 4. conversations  (1:1 with tickets)
-- ============================================================
CREATE TABLE conversations (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id   UUID        NOT NULL UNIQUE REFERENCES tickets(id) ON DELETE CASCADE,
    customer_id UUID        NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel     VARCHAR(20) NOT NULL CHECK (channel IN ('web', 'gmail', 'whatsapp')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversations_customer_id
    ON conversations (customer_id);

-- ============================================================
-- 5. messages
-- ============================================================
CREATE TABLE messages (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    direction       VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    channel         VARCHAR(20) NOT NULL CHECK (channel IN ('web', 'gmail', 'whatsapp')),
    content         TEXT        NOT NULL,
    sentiment       FLOAT       CHECK (sentiment >= 0 AND sentiment <= 1),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conversation_chrono
    ON messages (conversation_id, created_at);

-- ============================================================
-- 6. knowledge_base
-- ============================================================
CREATE TABLE knowledge_base (
    id         UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    title      VARCHAR(255)  NOT NULL,
    content    TEXT          NOT NULL,
    category   VARCHAR(50)   NOT NULL,
    embedding  VECTOR(1536),
    created_at TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- IVFFlat index for cosine similarity search
-- lists = 10 is appropriate for < 1000 articles
CREATE INDEX idx_knowledge_base_embedding
    ON knowledge_base
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

-- ============================================================
-- 7. channel_configs
-- ============================================================
CREATE TABLE channel_configs (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    channel        VARCHAR(20) NOT NULL UNIQUE
                               CHECK (channel IN ('web', 'gmail', 'whatsapp')),
    response_style VARCHAR(50) NOT NULL,
    max_length     INTEGER     NOT NULL,
    enabled        BOOLEAN     NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed channel configurations
INSERT INTO channel_configs (channel, response_style, max_length, enabled) VALUES
    ('web',      'semi-formal',     1500, true),
    ('gmail',    'formal',          2500, true),
    ('whatsapp', 'conversational',  800,  true);

-- ============================================================
-- 8. agent_metrics
-- ============================================================
CREATE TABLE agent_metrics (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id       UUID        REFERENCES customers(id),
    ticket_id         UUID        REFERENCES tickets(id),
    channel           VARCHAR(20) NOT NULL,
    response_time_ms  INTEGER     NOT NULL,
    sentiment         FLOAT,
    resolution_type   VARCHAR(30) NOT NULL
                                  CHECK (resolution_type IN ('auto_resolved', 'escalated', 'error')),
    escalation_reason TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_metrics_channel_time
    ON agent_metrics (channel, created_at);

COMMIT;
