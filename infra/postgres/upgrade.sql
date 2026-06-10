-- ════════════════════════════════════════════════════════════════════════════
--  staffKM — idempotent schema upgrade（db-migrate 每次部署都會跑）
-- ════════════════════════════════════════════════════════════════════════════
--
--  為什麼存在：init.sql 只在「DB 第一次建立（空資料夾）」時由 postgres entrypoint 跑一次。
--  既有部署升級時 init.sql 不會重跑 → 程式若有新欄位/索引，舊 DB 補不進去 → 啟動/查詢炸
--  （v5.12 must_change_password 漏補 → 既有部署登入失敗即此雷）。
--
--  紀律（重要）：任何加進 init.sql 的「新欄位 / 新索引 / 型別放寬」，**同一個 PR 也要在這裡**
--  補一條對應的 idempotent DDL。本檔每次部署重跑，所以：
--    ✅ 只放「加法、可重複執行」DDL：ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS /
--       ALTER COLUMN ... DROP NOT NULL 等。
--    ❌ 不要放破壞性 / 一次性語句：DROP COLUMN、改維度的 ALTER TYPE ... USING NULL（會清資料）、
--       seed/UPDATE 資料（會每次部署覆寫客戶資料）。那類請走專屬一次性 migration。
--  全新 DB 跑這支只是一堆 no-op（init.sql 已建好），無害。
--
--  ⚠ 注意：這裡**不**把 admin 設成 must_change_password=true —— 那只屬 init.sql（全新出廠），
--    既有部署的 admin 維持原密碼、不被每次部署強制改密。
-- ════════════════════════════════════════════════════════════════════════════

-- v5.12: 首次登入強制改密（欄位本身；admin 出廠標記只在 init.sql）
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS must_change_password boolean DEFAULT false NOT NULL;

-- v5.12: credit_ledger.reference 去重 backstop（add_credits 並發同 reference 防重複加值）
CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_ledger_reference
    ON public.credit_ledger(reference) WHERE reference IS NOT NULL;

-- （刻意不含）long_term_memories.embedding 1536→1024 維度變更：屬破壞性 ALTER TYPE，且該欄
--   目前休眠（走 FTS、無資料）。全新部署由 init.sql 給 1024；既有部署維持原樣，不在此每次重跑。

-- v5.13 #1 small-to-big：父子塊。paragraphs.parent_id + 獨立 paragraph_parents 表（不嵌入、不檢索）。
ALTER TABLE public.paragraphs
    ADD COLUMN IF NOT EXISTS parent_id uuid;
CREATE TABLE IF NOT EXISTS public.paragraph_parents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    knowledge_base_id uuid NOT NULL,
    workspace_id uuid,
    content text NOT NULL,
    order_index integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
DO $$ BEGIN
    ALTER TABLE ONLY public.paragraph_parents ADD CONSTRAINT paragraph_parents_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object OR duplicate_table OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.paragraph_parents ADD CONSTRAINT paragraph_parents_document_fk
        FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object OR duplicate_table OR invalid_table_definition THEN NULL; END $$;
CREATE INDEX IF NOT EXISTS idx_paragraph_parents_doc ON public.paragraph_parents(document_id);
CREATE INDEX IF NOT EXISTS idx_paragraphs_parent ON public.paragraphs(parent_id);

-- v5.13 LLM Wiki：kb_wiki_pages（用 LLM 把知識庫整理成可瀏覽百科）
CREATE TABLE IF NOT EXISTS public.kb_wiki_pages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    knowledge_base_id uuid NOT NULL,
    document_id uuid,
    workspace_id uuid,
    title character varying(256) NOT NULL,
    content text NOT NULL,
    order_index integer DEFAULT 0 NOT NULL,
    is_index boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
DO $$ BEGIN
    ALTER TABLE ONLY public.kb_wiki_pages ADD CONSTRAINT kb_wiki_pages_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object OR duplicate_table OR invalid_table_definition THEN NULL; END $$;
CREATE INDEX IF NOT EXISTS idx_kb_wiki_pages_kb ON public.kb_wiki_pages(knowledge_base_id, order_index);

-- v5.13 #2：記住使用者上次使用的 workspace（跨裝置/來源，取代僅 localStorage）
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS last_workspace_id uuid;
