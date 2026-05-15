-- =====================================================================
-- Migration 0001 — Multi-tenant workspace + member（RFC-001 Stage 1）
-- 可重入：所有語句使用 IF NOT EXISTS / DO blocks
-- 反向：見 0001_workspace_down.sql
-- =====================================================================

-- ─── 1. workspace 表 ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workspace (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         VARCHAR(128) NOT NULL,
    slug         VARCHAR(64)  NOT NULL,
    description  VARCHAR(512),
    plan         VARCHAR(32)  NOT NULL DEFAULT 'free',
    quota_meta   JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_slug ON workspace(slug)
    WHERE deleted_at IS NULL;


-- ─── 2. workspace_member 表 ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workspace_member (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id  UUID NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    role          VARCHAR(32) NOT NULL DEFAULT 'viewer',
    invited_by    UUID,
    invited_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    joined_at     TIMESTAMPTZ,
    is_active     BOOLEAN     NOT NULL DEFAULT true,
    CONSTRAINT uniq_workspace_member UNIQUE (workspace_id, user_id),
    CONSTRAINT chk_role CHECK (role IN ('owner','admin','editor','viewer'))
);

CREATE INDEX IF NOT EXISTS idx_member_user ON workspace_member(user_id);


-- ─── 3. 既有業務表加 workspace_id（過渡期 nullable）─────────────────
-- 等所有舊資料遷移完並上線後，再 ALTER ... SET NOT NULL（在後續 migration）

DO $$
DECLARE
    t TEXT;
    tables TEXT[] := ARRAY[
        'knowledge_bases',
        'documents',
        'paragraphs',
        'paragraph_embeddings',
        'applications',
        'ai_models',
        'model_providers',
        'application_chats',
        'application_chat_records',
        'application_api_keys'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = t) THEN
            EXECUTE format(
                'ALTER TABLE %I ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspace(id)',
                t
            );
            EXECUTE format(
                'CREATE INDEX IF NOT EXISTS idx_%s_workspace ON %I(workspace_id)',
                t, t
            );
            RAISE NOTICE '✓ added workspace_id to %', t;
        ELSE
            RAISE NOTICE '⊘ skipped % (table not exist yet)', t;
        END IF;
    END LOOP;
END $$;


-- ─── 4. Bootstrap "default" workspace 收容舊資料 ───────────────────
-- 給沒有 workspace_id 的舊 row 一個 fallback；新環境跳過

INSERT INTO workspace (id, name, slug, description, plan)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Default',
    'default',
    '初次安裝預設工作區，收容遷移前的所有舊資料',
    'free'
)
ON CONFLICT DO NOTHING;


-- ─── 5. 把現有 admin user 加為 default workspace 的 owner ───────────
-- 假設 users 表中 username = 'admin' 是 superadmin
INSERT INTO workspace_member (workspace_id, user_id, role, joined_at, is_active)
SELECT
    '00000000-0000-0000-0000-000000000001'::uuid,
    u.id,
    'owner',
    now(),
    true
FROM users u
WHERE u.username = 'admin'
  AND NOT EXISTS (
    SELECT 1 FROM workspace_member wm
    WHERE wm.workspace_id = '00000000-0000-0000-0000-000000000001'::uuid
      AND wm.user_id = u.id
  );


-- ─── 6. 回填既有資料的 workspace_id = default ──────────────────────
DO $$
DECLARE
    t TEXT;
    tables TEXT[] := ARRAY[
        'knowledge_bases', 'documents', 'paragraphs', 'paragraph_embeddings',
        'applications', 'ai_models', 'model_providers',
        'application_chats', 'application_chat_records', 'application_api_keys'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = t AND column_name = 'workspace_id') THEN
            EXECUTE format(
                'UPDATE %I SET workspace_id = ''00000000-0000-0000-0000-000000000001'' WHERE workspace_id IS NULL',
                t
            );
        END IF;
    END LOOP;
END $$;


COMMENT ON TABLE workspace        IS 'RFC-001: 多租戶工作區';
COMMENT ON TABLE workspace_member IS 'RFC-001: User × Workspace × Role 關聯';
