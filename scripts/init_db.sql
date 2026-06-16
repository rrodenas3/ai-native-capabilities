-- ai-native-capabilities — PostgreSQL initialisation
-- Runs automatically via docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for BM25-style lexical search

-- Episodic memory table (shared across capabilities)
CREATE TABLE IF NOT EXISTS episodic_memory (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capability  TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    run_id      TEXT,
    event_type  TEXT NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector(1536),           -- text-embedding-3-large dimensions
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS episodic_memory_embedding_idx
    ON episodic_memory USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS episodic_memory_capability_idx
    ON episodic_memory (capability, created_at DESC);

-- Semantic memory / document chunks (per capability, capability prefixed)
CREATE TABLE IF NOT EXISTS document_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capability      TEXT NOT NULL,
    doc_id          TEXT NOT NULL,
    chunk_index     INT NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(1536),
    metadata        JSONB DEFAULT '{}',
    access_tier     TEXT DEFAULT 'internal',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (capability, doc_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS doc_chunks_embedding_idx
    ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS doc_chunks_content_trgm_idx
    ON document_chunks USING gin (content gin_trgm_ops);

-- Audit trail (immutable — no UPDATE/DELETE)
CREATE TABLE IF NOT EXISTS audit_trail (
    id              BIGSERIAL PRIMARY KEY,
    capability      TEXT NOT NULL,
    run_id          TEXT,
    session_id      TEXT,
    event_type      TEXT NOT NULL,
    agent_name      TEXT,
    action          TEXT,
    payload         JSONB DEFAULT '{}',
    decision        TEXT,
    approved_by     TEXT,
    cost_usd        NUMERIC(10, 6),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Revoke UPDATE/DELETE on audit_trail to enforce immutability
REVOKE UPDATE, DELETE ON audit_trail FROM PUBLIC;

CREATE INDEX IF NOT EXISTS audit_trail_run_idx   ON audit_trail (run_id);
CREATE INDEX IF NOT EXISTS audit_trail_cap_idx   ON audit_trail (capability, created_at DESC);

-- LangGraph checkpoints (used by Cap-04 for durable execution)
CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
    thread_id       TEXT NOT NULL,
    checkpoint_ns   TEXT NOT NULL DEFAULT '',
    checkpoint_id   TEXT NOT NULL,
    parent_id       TEXT,
    type            TEXT,
    checkpoint      BYTEA NOT NULL,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

COMMENT ON TABLE langgraph_checkpoints IS 'LangGraph durable execution state — Cap-04 Autonomous Operations';
COMMENT ON TABLE audit_trail IS 'Immutable event log — UPDATE and DELETE are revoked';
COMMENT ON TABLE document_chunks IS 'Chunked document embeddings for semantic retrieval';
COMMENT ON TABLE episodic_memory IS 'Agent episodic memory — past events and sessions';
