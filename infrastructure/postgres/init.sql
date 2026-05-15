-- StaffKM 資料庫初始化腳本
-- 啟用 pgvector 擴充功能

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 支援中文全文搜尋

-- ── 使用者資料表 ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(64) NOT NULL UNIQUE,
    email           VARCHAR(256) UNIQUE,
    display_name    VARCHAR(128),
    password_hash   VARCHAR(256),
    ldap_dn         VARCHAR(512),
    status          VARCHAR(32) NOT NULL DEFAULT 'active',
    roles           TEXT[] NOT NULL DEFAULT '{"user"}',
    department      VARCHAR(128),
    tenant_id       VARCHAR(64),
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    avatar_url      VARCHAR(512),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      VARCHAR(64),
    updated_by      VARCHAR(64)
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- ── 知識庫資料表 ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    status          VARCHAR(32) NOT NULL DEFAULT 'active',
    embedding_model VARCHAR(64) NOT NULL DEFAULT 'text-embedding-3-small',
    vector_store_type VARCHAR(32) NOT NULL DEFAULT 'pgvector',
    meta            JSONB NOT NULL DEFAULT '{}',
    is_public       BOOLEAN NOT NULL DEFAULT FALSE,
    tenant_id       VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      VARCHAR(64),
    updated_by      VARCHAR(64)
);

-- ── 文件資料表 ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id   UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    name                VARCHAR(256) NOT NULL,
    file_type           VARCHAR(32),
    file_size           INTEGER NOT NULL DEFAULT 0,
    storage_path        VARCHAR(512),
    status              VARCHAR(32) NOT NULL DEFAULT 'pending',
    paragraph_count     INTEGER NOT NULL DEFAULT 0,
    char_count          INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    meta                JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          VARCHAR(64),
    updated_by          VARCHAR(64)
);

CREATE INDEX idx_documents_kb_id ON documents(knowledge_base_id);
CREATE INDEX idx_documents_status ON documents(status);

-- ── 段落資料表 ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS paragraphs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    knowledge_base_id   UUID NOT NULL,
    content             TEXT NOT NULL,
    title               VARCHAR(256),
    order_index         INTEGER NOT NULL DEFAULT 0,
    char_count          INTEGER NOT NULL DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    meta                JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          VARCHAR(64),
    updated_by          VARCHAR(64)
);

CREATE INDEX idx_paragraphs_doc_id ON paragraphs(document_id);
CREATE INDEX idx_paragraphs_kb_id ON paragraphs(knowledge_base_id);
-- 全文搜尋索引（支援繁體中文 simple parser）
CREATE INDEX idx_paragraphs_fts ON paragraphs USING gin(to_tsvector('simple', content));

-- ── 向量嵌入資料表（分離的資料層）─────────────────────
CREATE TABLE IF NOT EXISTS paragraph_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    kb_id           UUID NOT NULL,
    embedding       vector(1536),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_para_embed_kb ON paragraph_embeddings(kb_id);
CREATE INDEX idx_para_embed_vector ON paragraph_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── 對話 Session 資料表 ───────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(64) NOT NULL,
    scenario_id     VARCHAR(64) NOT NULL,
    title           VARCHAR(256),
    kb_ids          JSONB NOT NULL DEFAULT '[]',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    message_count   INTEGER NOT NULL DEFAULT 0,
    tenant_id       VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      VARCHAR(64),
    updated_by      VARCHAR(64)
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);

-- ── 訊息資料表 ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role                VARCHAR(16) NOT NULL,  -- user / assistant / system
    content             TEXT NOT NULL,
    citations           JSONB NOT NULL DEFAULT '[]',
    token_count         INTEGER NOT NULL DEFAULT 0,
    meta                JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          VARCHAR(64),
    updated_by          VARCHAR(64)
);

CREATE INDEX idx_messages_conv_id ON messages(conversation_id);

-- ── 稽核日誌資料表（獨立資料層）──────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id          UUID        NOT NULL DEFAULT gen_random_uuid(),
    user_id     VARCHAR(64),
    action      VARCHAR(128) NOT NULL,
    resource    VARCHAR(64),
    resource_id VARCHAR(64),
    ip_address  INET,
    user_agent  TEXT,
    payload     JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- 按月分區（範例：2026 年）
CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE audit_logs_2026_02 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE audit_logs_2026_03 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE audit_logs_2026_04 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE audit_logs_2026_05 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE audit_logs_2026_06 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE audit_logs_2026_07 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE audit_logs_2026_08 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE audit_logs_2026_09 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE audit_logs_2026_10 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE audit_logs_2026_11 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE audit_logs_2026_12 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- ── 模型提供者資料表 ─────────────────────────────────
CREATE TABLE IF NOT EXISTS model_providers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(64) NOT NULL,
    provider_type   VARCHAR(32) NOT NULL,  -- openai / ollama / azure / anthropic / custom
    base_url        VARCHAR(512),
    api_key_enc     TEXT,                  -- AES 加密後的 api_key
    status          VARCHAR(16) NOT NULL DEFAULT 'active',
    config          JSONB NOT NULL DEFAULT '{}',
    tenant_id       VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      VARCHAR(64),
    updated_by      VARCHAR(64)
);

-- ── 模型定義資料表 ────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_models (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id     UUID NOT NULL REFERENCES model_providers(id) ON DELETE CASCADE,
    model_name      VARCHAR(128) NOT NULL,
    model_type      VARCHAR(32) NOT NULL,  -- llm / embedding / reranker / tts / stt
    display_name    VARCHAR(128),
    config          JSONB NOT NULL DEFAULT '{}',
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    status          VARCHAR(16) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_models_provider ON ai_models(provider_id);
CREATE INDEX idx_ai_models_type ON ai_models(model_type);

-- ── AI 應用資料表（Application Builder）────────────────
CREATE TABLE IF NOT EXISTS applications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(128) NOT NULL,
    description         TEXT,
    icon                VARCHAR(512),
    type                VARCHAR(32) NOT NULL DEFAULT 'simple',  -- simple / workflow
    status              VARCHAR(16) NOT NULL DEFAULT 'published',
    llm_model_id        UUID REFERENCES ai_models(id) ON DELETE SET NULL,
    system_prompt       TEXT,
    welcome_message     TEXT,
    suggested_questions JSONB NOT NULL DEFAULT '[]',
    knowledge_base_ids  JSONB NOT NULL DEFAULT '[]',
    config              JSONB NOT NULL DEFAULT '{}',
    is_public           BOOLEAN NOT NULL DEFAULT FALSE,
    tenant_id           VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          VARCHAR(64),
    updated_by          VARCHAR(64)
);

CREATE INDEX idx_applications_type ON applications(type);
CREATE INDEX idx_applications_status ON applications(status);

-- ── 應用工作流節點資料表 ──────────────────────────────
CREATE TABLE IF NOT EXISTS workflow_nodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    node_type       VARCHAR(64) NOT NULL,
    node_key        VARCHAR(64) NOT NULL,
    label           VARCHAR(128),
    position        JSONB NOT NULL DEFAULT '{"x":0,"y":0}',
    config          JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workflow_nodes_app ON workflow_nodes(application_id);

-- ── 應用工作流邊 ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS workflow_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    source_node_key VARCHAR(64) NOT NULL,
    target_node_key VARCHAR(64) NOT NULL,
    condition       JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── API Key 資料表（外部嵌入存取）────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(128) NOT NULL,
    key_hash        VARCHAR(256) NOT NULL UNIQUE,
    key_prefix      VARCHAR(16) NOT NULL,  -- 顯示用前綴，如 sk-xxxx
    application_id  UUID REFERENCES applications(id) ON DELETE CASCADE,
    permissions     TEXT[] NOT NULL DEFAULT '{"chat"}',
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    status          VARCHAR(16) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      VARCHAR(64)
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_app ON api_keys(application_id);

-- ── 長期記憶資料表 ────────────────────────────────────
CREATE TABLE IF NOT EXISTS long_term_memories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(64) NOT NULL,
    application_id  UUID REFERENCES applications(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    memory_type     VARCHAR(32) NOT NULL DEFAULT 'summary',  -- summary / fact / preference
    importance      INTEGER NOT NULL DEFAULT 5,  -- 1-10
    embedding       vector(1536),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ltm_user ON long_term_memories(user_id);
CREATE INDEX idx_ltm_app ON long_term_memories(application_id);

-- ── 觸發器資料表 ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS triggers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(128) NOT NULL,
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    trigger_type    VARCHAR(32) NOT NULL,  -- schedule / webhook / event
    config          JSONB NOT NULL DEFAULT '{}',
    input_template  TEXT,
    status          VARCHAR(16) NOT NULL DEFAULT 'active',
    last_run_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      VARCHAR(64)
);

-- ── 預設管理員帳號 ────────────────────────────────────
-- 密碼: Admin@2026 (bcrypt hash)
INSERT INTO users (username, display_name, password_hash, roles, is_superuser, status)
VALUES (
    'admin',
    '系統管理員',
    '$2b$12$G6QzMyJa/htFRTBxqWoL5.g8mHheep4qQgJbbRS2MFSEUIrhzwiU2',
    ARRAY['admin', 'user'],
    TRUE,
    'active'
) ON CONFLICT (username) DO NOTHING;

-- ── 預設 OpenAI 模型提供者（需自行填入 api_key）────────
INSERT INTO model_providers (name, provider_type, base_url, status, config)
VALUES (
    'OpenAI',
    'openai',
    'https://api.openai.com/v1',
    'active',
    '{"timeout": 60}'
) ON CONFLICT DO NOTHING;

-- ── 預設 AI 應用（SOP 助理）────────────────────────────
INSERT INTO applications (name, description, type, system_prompt, welcome_message, suggested_questions, is_public)
VALUES (
    'SOP 作業助理',
    '回答各類標準作業程序（SOP）相關問題',
    'simple',
    '你是一位熟悉公司各項標準作業程序的行政助理，請根據知識庫內容精確回答員工的 SOP 相關問題。若找不到相關資料，請誠實告知並建議聯繫相關部門。',
    '您好！我是 SOP 作業助理，可以幫您查詢各類標準作業程序。請問有什麼需要協助的嗎？',
    '["如何申請出差？", "請假流程是什麼？", "採購申請需要哪些文件？"]',
    TRUE
) ON CONFLICT DO NOTHING;
