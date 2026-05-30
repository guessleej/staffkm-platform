-- staffKM init.sql — 由本機(可運作) DB 匯出，全新部署用
-- 產生: pg_dump schema-only(73 tables) + bootstrap seed(users/workspace/workspace_member/system_settings)
-- ⚠ 預設管理員密碼為 bootstrap 預設值（見部署文件 docs/deploy/production-deploy.md）。
--   正式部署「首次登入後務必立即更改密碼」，勿沿用預設值對外。

--
-- PostgreSQL database dump
--

\restrict RiWRDyAsmeaIgD3kCMzNXm5mwZonBIkVKqTqwASmxSXgT8Bo5sggNWtSwqAXRRc

-- Dumped from database version 16.13 (Debian 16.13-1.pgdg12+1)
-- Dumped by pg_dump version 16.13 (Debian 16.13-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_models; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_models (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    provider_id uuid NOT NULL,
    model_name character varying(128) NOT NULL,
    model_type character varying(32) NOT NULL,
    display_name character varying(128),
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    status character varying(16) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    price_per_1k_input_usd numeric(10,6),
    price_per_1k_output_usd numeric(10,6),
    price_per_image_usd numeric(10,6),
    price_per_second_usd numeric(10,6),
    price_per_1k_chars_usd numeric(10,6),
    price_per_call_usd numeric(10,6)
);


--
-- Name: alembic_version_agent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version_agent (
    version_num character varying(32) NOT NULL
);


--
-- Name: alembic_version_auth; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version_auth (
    version_num character varying(32) NOT NULL
);


--
-- Name: alembic_version_chat; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version_chat (
    version_num character varying(32) NOT NULL
);


--
-- Name: alembic_version_knowledge; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version_knowledge (
    version_num character varying(32) NOT NULL
);


--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_keys (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(128) NOT NULL,
    key_hash character varying(256) NOT NULL,
    key_prefix character varying(16) NOT NULL,
    application_id uuid,
    permissions text[] DEFAULT '{chat}'::text[] NOT NULL,
    last_used_at timestamp with time zone,
    expires_at timestamp with time zone,
    status character varying(16) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(64),
    workspace_id uuid
);


--
-- Name: application_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.application_versions (
    id uuid NOT NULL,
    application_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    version_number integer NOT NULL,
    snapshot jsonb NOT NULL,
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


--
-- Name: applications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.applications (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(128) NOT NULL,
    description text,
    icon character varying(512),
    type character varying(32) DEFAULT 'simple'::character varying NOT NULL,
    status character varying(16) DEFAULT 'published'::character varying NOT NULL,
    llm_model_id uuid,
    system_prompt text,
    welcome_message text,
    suggested_questions jsonb DEFAULT '[]'::jsonb NOT NULL,
    knowledge_base_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_public boolean DEFAULT false NOT NULL,
    tenant_id character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(64),
    updated_by character varying(64),
    workspace_id uuid,
    skill_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    folder_id uuid,
    workflow_manager character varying(16) DEFAULT 'simple'::character varying NOT NULL
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
)
PARTITION BY RANGE (created_at);


--
-- Name: audit_logs_2026_01; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_01 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_02; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_02 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_03; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_03 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_04; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_04 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_05; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_05 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_06; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_06 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_07; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_07 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_08; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_08 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_09; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_09 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_10; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_10 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_11; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_11 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: audit_logs_2026_12; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs_2026_12 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64),
    action character varying(128) NOT NULL,
    resource character varying(64),
    resource_id character varying(64),
    ip_address inet,
    user_agent text,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    actor_username character varying(64),
    entity_label character varying(256)
);


--
-- Name: billing_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.billing_accounts (
    workspace_id uuid NOT NULL,
    stripe_customer_id character varying(64),
    stripe_subscription_id character varying(64),
    plan character varying(32) DEFAULT 'trial'::character varying NOT NULL,
    status character varying(32) DEFAULT 'active'::character varying NOT NULL,
    credits_balance numeric(12,6) DEFAULT 0 NOT NULL,
    billing_cycle_anchor timestamp with time zone,
    current_period_start timestamp with time zone,
    current_period_end timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: billing_invoices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.billing_invoices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id uuid NOT NULL,
    stripe_invoice_id character varying(64),
    amount_usd numeric(12,2) NOT NULL,
    currency character varying(8) DEFAULT 'usd'::character varying,
    status character varying(32) NOT NULL,
    period_start timestamp with time zone,
    period_end timestamp with time zone,
    invoice_pdf_url text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(64) NOT NULL,
    scenario_id character varying(64),
    title character varying(256),
    kb_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    message_count integer DEFAULT 0 NOT NULL,
    tenant_id character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(64),
    updated_by character varying(64),
    workspace_id uuid,
    share_token text,
    application_id uuid
);


--
-- Name: credit_ledger; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credit_ledger (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id uuid NOT NULL,
    delta_usd numeric(12,6) NOT NULL,
    reason character varying(32) NOT NULL,
    reference character varying(128),
    balance_after numeric(12,6) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: data_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_sources (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    name character varying(128) NOT NULL,
    description text,
    kind character varying(32) DEFAULT 'postgres'::character varying NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    last_synced_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    folder_id uuid
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    knowledge_base_id uuid NOT NULL,
    name character varying(256) NOT NULL,
    file_type character varying(32),
    file_size integer DEFAULT 0 NOT NULL,
    storage_path character varying(512),
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    paragraph_count integer DEFAULT 0 NOT NULL,
    char_count integer DEFAULT 0 NOT NULL,
    error_message text,
    meta jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(64),
    updated_by character varying(64),
    workspace_id uuid,
    tags jsonb DEFAULT '[]'::jsonb NOT NULL,
    hit_strategy character varying(16) DEFAULT 'rag'::character varying NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    questions jsonb DEFAULT '[]'::jsonb NOT NULL
);


--
-- Name: entity_folders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_folders (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    entity_kind character varying(32) NOT NULL,
    parent_id uuid,
    name character varying(128) NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


--
-- Name: event_trigger_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_trigger_runs (
    id uuid NOT NULL,
    trigger_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    fired_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    status character varying(16) DEFAULT 'queued'::character varying NOT NULL,
    output_summary text,
    error text,
    tokens_used bigint DEFAULT 0 NOT NULL,
    cost_usd numeric(12,6) DEFAULT 0 NOT NULL,
    paused_at timestamp with time zone,
    resumed_at timestamp with time zone,
    resume_node character varying(64)
);


--
-- Name: event_triggers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_triggers (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    application_id uuid NOT NULL,
    name character varying(128) NOT NULL,
    kind character varying(16) DEFAULT 'interval'::character varying NOT NULL,
    cron_expr character varying(64),
    interval_sec integer,
    input_template text DEFAULT ''::text NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    next_fire_at timestamp with time zone,
    last_fired_at timestamp with time zone,
    last_status character varying(16),
    last_error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


--
-- Name: idempotency_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.idempotency_keys (
    key character varying(128) NOT NULL,
    endpoint character varying(128) NOT NULL,
    workspace_id uuid,
    response_json jsonb,
    status_code integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone DEFAULT (now() + '24:00:00'::interval) NOT NULL
);


--
-- Name: kb_communities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kb_communities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id uuid NOT NULL,
    knowledge_base_id uuid NOT NULL,
    level integer DEFAULT 0 NOT NULL,
    title text,
    summary text,
    entity_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    cohesion_score real,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: kb_entities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kb_entities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id uuid NOT NULL,
    knowledge_base_id uuid NOT NULL,
    name text NOT NULL,
    norm_name text NOT NULL,
    aliases jsonb DEFAULT '[]'::jsonb NOT NULL,
    entity_type text DEFAULT 'concept'::text NOT NULL,
    description text,
    embedding public.vector(1024),
    mention_count integer DEFAULT 0 NOT NULL,
    confidence real DEFAULT 1.0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: kb_entity_mentions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kb_entity_mentions (
    entity_id uuid NOT NULL,
    paragraph_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    quote text
);


--
-- Name: kb_folders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kb_folders (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    parent_id uuid,
    name character varying(128) NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


--
-- Name: kb_grants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kb_grants (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    kb_id uuid NOT NULL,
    principal_type character varying(16) NOT NULL,
    principal_id character varying(128) NOT NULL,
    access character varying(16) DEFAULT 'read'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


--
-- Name: kb_relation_mentions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kb_relation_mentions (
    relation_id uuid NOT NULL,
    paragraph_id uuid NOT NULL,
    workspace_id uuid NOT NULL
);


--
-- Name: kb_relations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kb_relations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id uuid NOT NULL,
    knowledge_base_id uuid NOT NULL,
    src_entity_id uuid NOT NULL,
    dst_entity_id uuid NOT NULL,
    relation_type text NOT NULL,
    description text,
    weight real DEFAULT 1.0 NOT NULL,
    confidence real DEFAULT 1.0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: knowledge_bases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_bases (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(128) NOT NULL,
    description text,
    status character varying(32) DEFAULT 'active'::character varying NOT NULL,
    embedding_model character varying(64) DEFAULT 'text-embedding-3-small'::character varying NOT NULL,
    vector_store_type character varying(32) DEFAULT 'pgvector'::character varying NOT NULL,
    meta jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_public boolean DEFAULT false NOT NULL,
    tenant_id character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(64),
    updated_by character varying(64),
    workspace_id uuid,
    folder_id uuid,
    chunk_strategy character varying(16) DEFAULT 'auto'::character varying NOT NULL,
    chunk_size integer DEFAULT 512 NOT NULL,
    chunk_overlap integer DEFAULT 64 NOT NULL,
    source_type character varying(16) DEFAULT 'manual'::character varying NOT NULL,
    source_workflow_id uuid,
    source_url text,
    last_synced_at timestamp with time zone,
    sync_status character varying(16),
    sync_error text,
    graph_enabled boolean DEFAULT false NOT NULL
);


--
-- Name: long_term_memories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.long_term_memories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    application_id uuid,
    content text NOT NULL,
    memory_type character varying(32) DEFAULT 'summary'::character varying NOT NULL,
    importance integer DEFAULT 5 NOT NULL,
    embedding public.vector(1024),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid,
    scope character varying(16) DEFAULT 'user'::character varying NOT NULL,
    tags jsonb DEFAULT '[]'::jsonb NOT NULL,
    access_count integer DEFAULT 0 NOT NULL,
    last_accessed_at timestamp with time zone,
    created_by uuid
);


--
-- Name: mcp_servers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mcp_servers (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    name character varying(128) NOT NULL,
    description text,
    transport character varying(16) DEFAULT 'http'::character varying NOT NULL,
    url text,
    command text,
    args jsonb DEFAULT '[]'::jsonb NOT NULL,
    env jsonb DEFAULT '{}'::jsonb NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    last_refreshed_at timestamp with time zone,
    last_error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


--
-- Name: mcp_tools_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mcp_tools_cache (
    id uuid NOT NULL,
    server_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    name character varying(128) NOT NULL,
    description text,
    input_schema jsonb DEFAULT '{}'::jsonb NOT NULL,
    refreshed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.messages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    conversation_id uuid NOT NULL,
    role character varying(16) NOT NULL,
    content text NOT NULL,
    citations jsonb DEFAULT '[]'::jsonb NOT NULL,
    token_count integer DEFAULT 0 NOT NULL,
    meta jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(64),
    updated_by character varying(64),
    workspace_id uuid
);


--
-- Name: model_providers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_providers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(64) NOT NULL,
    provider_type character varying(32) NOT NULL,
    base_url character varying(512),
    api_key_enc text,
    status character varying(16) DEFAULT 'active'::character varying NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    tenant_id character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(64),
    updated_by character varying(64),
    workspace_id uuid
);


--
-- Name: model_usage_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_usage_logs (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    user_id uuid,
    application_id uuid,
    provider_type character varying(32),
    model character varying(128),
    prompt_tokens integer DEFAULT 0 NOT NULL,
    completion_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer DEFAULT 0 NOT NULL,
    cost_usd numeric(12,6) DEFAULT 0 NOT NULL,
    latency_ms integer DEFAULT 0 NOT NULL,
    status character varying(16) DEFAULT 'ok'::character varying NOT NULL,
    error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    unit_type character varying(16),
    unit_count numeric(12,4),
    conversation_id uuid,
    message_id uuid,
    feature character varying(16)
);


--
-- Name: paragraph_embeddings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paragraph_embeddings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    paragraph_id uuid NOT NULL,
    kb_id uuid NOT NULL,
    embedding public.vector(1024),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid
);


--
-- Name: paragraphs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paragraphs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    knowledge_base_id uuid NOT NULL,
    content text NOT NULL,
    title character varying(256),
    order_index integer DEFAULT 0 NOT NULL,
    char_count integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    meta jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(64),
    updated_by character varying(64),
    search_vector tsvector,
    workspace_id uuid,
    qa_pairs jsonb DEFAULT '[]'::jsonb NOT NULL
);


--
-- Name: project_resources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_resources (
    project_id uuid NOT NULL,
    kind character varying(16) NOT NULL,
    resource_id character varying(64) NOT NULL,
    attached_at timestamp with time zone DEFAULT now() NOT NULL,
    attached_by uuid
);


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    name character varying(128) NOT NULL,
    description text,
    emoji character varying(8),
    system_prompt text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: quota_alert_fires; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quota_alert_fires (
    alert_id uuid NOT NULL,
    month date NOT NULL,
    fired_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: quota_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quota_alerts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id uuid NOT NULL,
    scope character varying(16) NOT NULL,
    threshold_pct integer NOT NULL,
    channel character varying(16) NOT NULL,
    target text NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_channel CHECK (((channel)::text = ANY ((ARRAY['email'::character varying, 'slack'::character varying, 'webhook'::character varying])::text[]))),
    CONSTRAINT chk_scope CHECK (((scope)::text = ANY ((ARRAY['workspace'::character varying, 'user'::character varying])::text[]))),
    CONSTRAINT chk_threshold CHECK (((threshold_pct >= 1) AND (threshold_pct <= 100)))
);


--
-- Name: region_conflict_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.region_conflict_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    detected_at timestamp with time zone DEFAULT now() NOT NULL,
    entity_type character varying(32) NOT NULL,
    entity_id character varying(64) NOT NULL,
    region_a character varying(32) NOT NULL,
    region_b character varying(32) NOT NULL,
    value_a jsonb,
    value_b jsonb,
    resolution character varying(16) DEFAULT 'pending'::character varying,
    resolved_value jsonb,
    resolved_at timestamp with time zone
);


--
-- Name: regions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.regions (
    id character varying(32) NOT NULL,
    name character varying(64) NOT NULL,
    db_url text,
    minio_endpoint text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: skills; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.skills (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    name character varying(128) NOT NULL,
    description text,
    prompt_template text DEFAULT ''::text NOT NULL,
    variables jsonb DEFAULT '[]'::jsonb NOT NULL,
    tags jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    folder_id uuid
);


--
-- Name: slow_query_explains; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.slow_query_explains (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    captured_at timestamp with time zone DEFAULT now() NOT NULL,
    duration_ms integer NOT NULL,
    sql_text text NOT NULL,
    sql_hash character varying(64) NOT NULL,
    explain_json jsonb,
    explain_error text
);


--
-- Name: system_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_settings (
    key character varying(64) NOT NULL,
    value jsonb NOT NULL,
    description text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by uuid
);


--
-- Name: task_heartbeats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_heartbeats (
    worker_name character varying(64) NOT NULL,
    pid integer,
    host character varying(128),
    started_at timestamp with time zone NOT NULL,
    last_beat timestamp with time zone NOT NULL,
    in_flight integer DEFAULT 0 NOT NULL
);


--
-- Name: template_ratings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.template_ratings (
    template_id uuid NOT NULL,
    user_id uuid NOT NULL,
    rating smallint NOT NULL,
    comment text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT template_ratings_rating_check CHECK (((rating >= 1) AND (rating <= 5)))
);


--
-- Name: tools; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tools (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    name character varying(128) NOT NULL,
    description text,
    kind character varying(32) DEFAULT 'http'::character varying NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    folder_id uuid,
    tool_type text,
    application_id uuid,
    input_schema jsonb DEFAULT '{}'::jsonb,
    output_schema jsonb DEFAULT '{}'::jsonb,
    code text
);


--
-- Name: triggers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.triggers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(128) NOT NULL,
    application_id uuid NOT NULL,
    trigger_type character varying(32) NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    input_template text,
    status character varying(16) DEFAULT 'active'::character varying NOT NULL,
    last_run_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(64)
);


--
-- Name: usage_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usage_reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id uuid NOT NULL,
    period_start timestamp with time zone NOT NULL,
    period_end timestamp with time zone NOT NULL,
    tokens_reported bigint DEFAULT 0 NOT NULL,
    cost_reported_usd numeric(12,6) DEFAULT 0 NOT NULL,
    stripe_event_id character varying(64),
    reported_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_quotas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_quotas (
    workspace_id uuid NOT NULL,
    user_id uuid NOT NULL,
    monthly_token_cap bigint,
    monthly_cost_cap_usd numeric(12,2),
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by uuid
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    username character varying(64) NOT NULL,
    email character varying(256),
    display_name character varying(128),
    password_hash character varying(256),
    ldap_dn character varying(512),
    status character varying(32) DEFAULT 'active'::character varying NOT NULL,
    roles text[] DEFAULT '{user}'::text[] NOT NULL,
    department character varying(128),
    tenant_id character varying(64),
    is_superuser boolean DEFAULT false NOT NULL,
    avatar_url character varying(512),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(64),
    updated_by character varying(64),
    oidc_sub character varying(256),
    oidc_issuer character varying(256),
    email_verified_at timestamp with time zone,
    verify_token character varying(128),
    verify_token_exp timestamp with time zone,
    reset_token character varying(128),
    reset_token_exp timestamp with time zone,
    allowed_login_methods character varying[]
);


--
-- Name: webhook_outbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_outbox (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id uuid,
    url text NOT NULL,
    method character varying(8) DEFAULT 'POST'::character varying NOT NULL,
    headers jsonb,
    body jsonb,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    next_retry_at timestamp with time zone DEFAULT now() NOT NULL,
    last_error text,
    last_status_code integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    delivered_at timestamp with time zone,
    source_type character varying(32),
    source_id uuid,
    CONSTRAINT chk_outbox_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'in_flight'::character varying, 'delivered'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: workflow_approvals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_approvals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    node_key character varying(64) NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    requester character varying(128),
    approver_id uuid,
    approver_note text,
    payload jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone,
    CONSTRAINT chk_approval_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying])::text[])))
);


--
-- Name: workflow_edges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_edges (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    application_id uuid NOT NULL,
    source_node_key character varying(64) NOT NULL,
    target_node_key character varying(64) NOT NULL,
    condition jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid
);


--
-- Name: workflow_nodes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_nodes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    application_id uuid NOT NULL,
    node_type character varying(64) NOT NULL,
    node_key character varying(64) NOT NULL,
    label character varying(128),
    "position" jsonb DEFAULT '{"x": 0, "y": 0}'::jsonb NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id uuid
);


--
-- Name: workflow_run_steps; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_run_steps (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid NOT NULL,
    step_index integer NOT NULL,
    node_key character varying(64) NOT NULL,
    node_type character varying(32) NOT NULL,
    status character varying(16) DEFAULT 'ok'::character varying NOT NULL,
    input_snapshot jsonb,
    output_snapshot jsonb,
    error text,
    attempts integer DEFAULT 1 NOT NULL,
    latency_ms integer,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone
);


--
-- Name: workflow_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_versions (
    id uuid NOT NULL,
    application_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    version_number integer NOT NULL,
    nodes jsonb DEFAULT '[]'::jsonb NOT NULL,
    edges jsonb DEFAULT '[]'::jsonb NOT NULL,
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


--
-- Name: workspace; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(128) NOT NULL,
    slug character varying(64) NOT NULL,
    description character varying(512),
    plan character varying(32) DEFAULT 'free'::character varying NOT NULL,
    quota_meta jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    trial_expires_at timestamp with time zone,
    trial_plan character varying(32),
    is_frozen boolean DEFAULT false NOT NULL,
    signup_email character varying(256),
    signup_source character varying(32),
    primary_region character varying(32) DEFAULT 'default'::character varying
);


--
-- Name: TABLE workspace; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.workspace IS 'RFC-001: 多租戶工作區';


--
-- Name: workspace_app_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace_app_templates (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    name character varying(128) NOT NULL,
    emoji character varying(8) DEFAULT '✨'::character varying NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    system_prompt text DEFAULT ''::text NOT NULL,
    welcome_message text DEFAULT ''::text NOT NULL,
    suggested_questions jsonb DEFAULT '[]'::jsonb NOT NULL,
    requires_kb boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    is_public boolean DEFAULT false NOT NULL,
    install_count integer DEFAULT 0 NOT NULL,
    publisher_name character varying(64),
    publisher_url text,
    cover_image_url text,
    category character varying(32),
    tags jsonb DEFAULT '[]'::jsonb,
    license character varying(32) DEFAULT 'MIT'::character varying,
    verified boolean DEFAULT false NOT NULL,
    rating_avg numeric(3,2),
    rating_count integer DEFAULT 0 NOT NULL
);


--
-- Name: workspace_member; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace_member (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role character varying(32) DEFAULT 'viewer'::character varying NOT NULL,
    invited_by uuid,
    invited_at timestamp with time zone DEFAULT now() NOT NULL,
    joined_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT chk_role CHECK (((role)::text = ANY ((ARRAY['owner'::character varying, 'admin'::character varying, 'editor'::character varying, 'viewer'::character varying])::text[])))
);


--
-- Name: TABLE workspace_member; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.workspace_member IS 'RFC-001: User × Workspace × Role 關聯';


--
-- Name: workspace_quotas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace_quotas (
    workspace_id uuid NOT NULL,
    monthly_token_cap bigint,
    monthly_cost_cap_usd numeric(12,2),
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by uuid
);


--
-- Name: audit_logs_2026_01; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_01 FOR VALUES FROM ('2026-01-01 00:00:00+08') TO ('2026-02-01 00:00:00+08');


--
-- Name: audit_logs_2026_02; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_02 FOR VALUES FROM ('2026-02-01 00:00:00+08') TO ('2026-03-01 00:00:00+08');


--
-- Name: audit_logs_2026_03; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_03 FOR VALUES FROM ('2026-03-01 00:00:00+08') TO ('2026-04-01 00:00:00+08');


--
-- Name: audit_logs_2026_04; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_04 FOR VALUES FROM ('2026-04-01 00:00:00+08') TO ('2026-05-01 00:00:00+08');


--
-- Name: audit_logs_2026_05; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_05 FOR VALUES FROM ('2026-05-01 00:00:00+08') TO ('2026-06-01 00:00:00+08');


--
-- Name: audit_logs_2026_06; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_06 FOR VALUES FROM ('2026-06-01 00:00:00+08') TO ('2026-07-01 00:00:00+08');


--
-- Name: audit_logs_2026_07; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_07 FOR VALUES FROM ('2026-07-01 00:00:00+08') TO ('2026-08-01 00:00:00+08');


--
-- Name: audit_logs_2026_08; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_08 FOR VALUES FROM ('2026-08-01 00:00:00+08') TO ('2026-09-01 00:00:00+08');


--
-- Name: audit_logs_2026_09; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_09 FOR VALUES FROM ('2026-09-01 00:00:00+08') TO ('2026-10-01 00:00:00+08');


--
-- Name: audit_logs_2026_10; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_10 FOR VALUES FROM ('2026-10-01 00:00:00+08') TO ('2026-11-01 00:00:00+08');


--
-- Name: audit_logs_2026_11; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_11 FOR VALUES FROM ('2026-11-01 00:00:00+08') TO ('2026-12-01 00:00:00+08');


--
-- Name: audit_logs_2026_12; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ATTACH PARTITION public.audit_logs_2026_12 FOR VALUES FROM ('2026-12-01 00:00:00+08') TO ('2027-01-01 00:00:00+08');


--
-- Name: ai_models ai_models_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_models
    ADD CONSTRAINT ai_models_pkey PRIMARY KEY (id);


--
-- Name: alembic_version_agent alembic_version_agent_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version_agent
    ADD CONSTRAINT alembic_version_agent_pkc PRIMARY KEY (version_num);


--
-- Name: alembic_version_auth alembic_version_auth_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version_auth
    ADD CONSTRAINT alembic_version_auth_pkc PRIMARY KEY (version_num);


--
-- Name: alembic_version_chat alembic_version_chat_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version_chat
    ADD CONSTRAINT alembic_version_chat_pkc PRIMARY KEY (version_num);


--
-- Name: alembic_version_knowledge alembic_version_knowledge_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version_knowledge
    ADD CONSTRAINT alembic_version_knowledge_pkc PRIMARY KEY (version_num);


--
-- Name: api_keys api_keys_key_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_key_hash_key UNIQUE (key_hash);


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: application_versions application_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_versions
    ADD CONSTRAINT application_versions_pkey PRIMARY KEY (id);


--
-- Name: applications applications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_01 audit_logs_2026_01_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_01
    ADD CONSTRAINT audit_logs_2026_01_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_02 audit_logs_2026_02_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_02
    ADD CONSTRAINT audit_logs_2026_02_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_03 audit_logs_2026_03_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_03
    ADD CONSTRAINT audit_logs_2026_03_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_04 audit_logs_2026_04_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_04
    ADD CONSTRAINT audit_logs_2026_04_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_05 audit_logs_2026_05_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_05
    ADD CONSTRAINT audit_logs_2026_05_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_06 audit_logs_2026_06_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_06
    ADD CONSTRAINT audit_logs_2026_06_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_07 audit_logs_2026_07_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_07
    ADD CONSTRAINT audit_logs_2026_07_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_08 audit_logs_2026_08_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_08
    ADD CONSTRAINT audit_logs_2026_08_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_09 audit_logs_2026_09_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_09
    ADD CONSTRAINT audit_logs_2026_09_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_10 audit_logs_2026_10_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_10
    ADD CONSTRAINT audit_logs_2026_10_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_11 audit_logs_2026_11_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_11
    ADD CONSTRAINT audit_logs_2026_11_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_logs_2026_12 audit_logs_2026_12_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs_2026_12
    ADD CONSTRAINT audit_logs_2026_12_pkey PRIMARY KEY (id, created_at);


--
-- Name: billing_accounts billing_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.billing_accounts
    ADD CONSTRAINT billing_accounts_pkey PRIMARY KEY (workspace_id);


--
-- Name: billing_invoices billing_invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.billing_invoices
    ADD CONSTRAINT billing_invoices_pkey PRIMARY KEY (id);


--
-- Name: billing_invoices billing_invoices_stripe_invoice_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.billing_invoices
    ADD CONSTRAINT billing_invoices_stripe_invoice_id_key UNIQUE (stripe_invoice_id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: credit_ledger credit_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_ledger
    ADD CONSTRAINT credit_ledger_pkey PRIMARY KEY (id);


--
-- Name: data_sources data_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: entity_folders entity_folders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_folders
    ADD CONSTRAINT entity_folders_pkey PRIMARY KEY (id);


--
-- Name: event_trigger_runs event_trigger_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_trigger_runs
    ADD CONSTRAINT event_trigger_runs_pkey PRIMARY KEY (id);


--
-- Name: event_triggers event_triggers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_triggers
    ADD CONSTRAINT event_triggers_pkey PRIMARY KEY (id);


--
-- Name: idempotency_keys idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (key, endpoint);


--
-- Name: kb_communities kb_communities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_communities
    ADD CONSTRAINT kb_communities_pkey PRIMARY KEY (id);


--
-- Name: kb_entities kb_entities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_entities
    ADD CONSTRAINT kb_entities_pkey PRIMARY KEY (id);


--
-- Name: kb_entity_mentions kb_entity_mentions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_entity_mentions
    ADD CONSTRAINT kb_entity_mentions_pkey PRIMARY KEY (entity_id, paragraph_id);


--
-- Name: kb_folders kb_folders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_folders
    ADD CONSTRAINT kb_folders_pkey PRIMARY KEY (id);


--
-- Name: kb_grants kb_grants_kb_id_principal_type_principal_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_grants
    ADD CONSTRAINT kb_grants_kb_id_principal_type_principal_id_key UNIQUE (kb_id, principal_type, principal_id);


--
-- Name: kb_grants kb_grants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_grants
    ADD CONSTRAINT kb_grants_pkey PRIMARY KEY (id);


--
-- Name: kb_relation_mentions kb_relation_mentions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_relation_mentions
    ADD CONSTRAINT kb_relation_mentions_pkey PRIMARY KEY (relation_id, paragraph_id);


--
-- Name: kb_relations kb_relations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_relations
    ADD CONSTRAINT kb_relations_pkey PRIMARY KEY (id);


--
-- Name: knowledge_bases knowledge_bases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_bases
    ADD CONSTRAINT knowledge_bases_pkey PRIMARY KEY (id);


--
-- Name: long_term_memories long_term_memories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.long_term_memories
    ADD CONSTRAINT long_term_memories_pkey PRIMARY KEY (id);


--
-- Name: mcp_servers mcp_servers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcp_servers
    ADD CONSTRAINT mcp_servers_pkey PRIMARY KEY (id);


--
-- Name: mcp_tools_cache mcp_tools_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcp_tools_cache
    ADD CONSTRAINT mcp_tools_cache_pkey PRIMARY KEY (id);


--
-- Name: mcp_tools_cache mcp_tools_cache_server_id_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcp_tools_cache
    ADD CONSTRAINT mcp_tools_cache_server_id_name_key UNIQUE (server_id, name);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: model_providers model_providers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_providers
    ADD CONSTRAINT model_providers_pkey PRIMARY KEY (id);


--
-- Name: model_usage_logs model_usage_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_usage_logs
    ADD CONSTRAINT model_usage_logs_pkey PRIMARY KEY (id);


--
-- Name: paragraph_embeddings paragraph_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paragraph_embeddings
    ADD CONSTRAINT paragraph_embeddings_pkey PRIMARY KEY (id);


--
-- Name: paragraphs paragraphs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paragraphs
    ADD CONSTRAINT paragraphs_pkey PRIMARY KEY (id);


--
-- Name: project_resources project_resources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_resources
    ADD CONSTRAINT project_resources_pkey PRIMARY KEY (project_id, kind, resource_id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: quota_alert_fires quota_alert_fires_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quota_alert_fires
    ADD CONSTRAINT quota_alert_fires_pkey PRIMARY KEY (alert_id, month);


--
-- Name: quota_alerts quota_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quota_alerts
    ADD CONSTRAINT quota_alerts_pkey PRIMARY KEY (id);


--
-- Name: region_conflict_log region_conflict_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.region_conflict_log
    ADD CONSTRAINT region_conflict_log_pkey PRIMARY KEY (id);


--
-- Name: regions regions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regions
    ADD CONSTRAINT regions_pkey PRIMARY KEY (id);


--
-- Name: skills skills_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.skills
    ADD CONSTRAINT skills_pkey PRIMARY KEY (id);


--
-- Name: slow_query_explains slow_query_explains_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.slow_query_explains
    ADD CONSTRAINT slow_query_explains_pkey PRIMARY KEY (id);


--
-- Name: system_settings system_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_pkey PRIMARY KEY (key);


--
-- Name: task_heartbeats task_heartbeats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_heartbeats
    ADD CONSTRAINT task_heartbeats_pkey PRIMARY KEY (worker_name);


--
-- Name: template_ratings template_ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_ratings
    ADD CONSTRAINT template_ratings_pkey PRIMARY KEY (template_id, user_id);


--
-- Name: tools tools_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tools
    ADD CONSTRAINT tools_pkey PRIMARY KEY (id);


--
-- Name: triggers triggers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triggers
    ADD CONSTRAINT triggers_pkey PRIMARY KEY (id);


--
-- Name: paragraph_embeddings uniq_para_embed; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paragraph_embeddings
    ADD CONSTRAINT uniq_para_embed UNIQUE (paragraph_id);


--
-- Name: workspace_member uniq_workspace_member; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_member
    ADD CONSTRAINT uniq_workspace_member UNIQUE (workspace_id, user_id);


--
-- Name: usage_reports usage_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_reports
    ADD CONSTRAINT usage_reports_pkey PRIMARY KEY (id);


--
-- Name: usage_reports usage_reports_workspace_id_period_start_period_end_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_reports
    ADD CONSTRAINT usage_reports_workspace_id_period_start_period_end_key UNIQUE (workspace_id, period_start, period_end);


--
-- Name: user_quotas user_quotas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_quotas
    ADD CONSTRAINT user_quotas_pkey PRIMARY KEY (workspace_id, user_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: webhook_outbox webhook_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_outbox
    ADD CONSTRAINT webhook_outbox_pkey PRIMARY KEY (id);


--
-- Name: workflow_approvals workflow_approvals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_approvals
    ADD CONSTRAINT workflow_approvals_pkey PRIMARY KEY (id);


--
-- Name: workflow_edges workflow_edges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_edges
    ADD CONSTRAINT workflow_edges_pkey PRIMARY KEY (id);


--
-- Name: workflow_nodes workflow_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_nodes
    ADD CONSTRAINT workflow_nodes_pkey PRIMARY KEY (id);


--
-- Name: workflow_run_steps workflow_run_steps_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_run_steps
    ADD CONSTRAINT workflow_run_steps_pkey PRIMARY KEY (id);


--
-- Name: workflow_versions workflow_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_versions
    ADD CONSTRAINT workflow_versions_pkey PRIMARY KEY (id);


--
-- Name: workspace_app_templates workspace_app_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_app_templates
    ADD CONSTRAINT workspace_app_templates_pkey PRIMARY KEY (id);


--
-- Name: workspace_member workspace_member_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_member
    ADD CONSTRAINT workspace_member_pkey PRIMARY KEY (id);


--
-- Name: workspace workspace_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace
    ADD CONSTRAINT workspace_pkey PRIMARY KEY (id);


--
-- Name: workspace_quotas workspace_quotas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_quotas
    ADD CONSTRAINT workspace_quotas_pkey PRIMARY KEY (workspace_id);


--
-- Name: idx_audit_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_action ON ONLY public.audit_logs USING btree (action);


--
-- Name: audit_logs_2026_01_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_01_action_idx ON public.audit_logs_2026_01 USING btree (action);


--
-- Name: idx_audit_logs_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_resource ON ONLY public.audit_logs USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_01_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_01_resource_resource_id_idx ON public.audit_logs_2026_01 USING btree (resource, resource_id);


--
-- Name: idx_audit_logs_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_user ON ONLY public.audit_logs USING btree (user_id);


--
-- Name: audit_logs_2026_01_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_01_user_id_idx ON public.audit_logs_2026_01 USING btree (user_id);


--
-- Name: idx_audit_logs_ws_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_ws_created ON ONLY public.audit_logs USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_01_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_01_workspace_id_created_at_idx ON public.audit_logs_2026_01 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_02_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_02_action_idx ON public.audit_logs_2026_02 USING btree (action);


--
-- Name: audit_logs_2026_02_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_02_resource_resource_id_idx ON public.audit_logs_2026_02 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_02_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_02_user_id_idx ON public.audit_logs_2026_02 USING btree (user_id);


--
-- Name: audit_logs_2026_02_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_02_workspace_id_created_at_idx ON public.audit_logs_2026_02 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_03_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_03_action_idx ON public.audit_logs_2026_03 USING btree (action);


--
-- Name: audit_logs_2026_03_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_03_resource_resource_id_idx ON public.audit_logs_2026_03 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_03_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_03_user_id_idx ON public.audit_logs_2026_03 USING btree (user_id);


--
-- Name: audit_logs_2026_03_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_03_workspace_id_created_at_idx ON public.audit_logs_2026_03 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_04_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_04_action_idx ON public.audit_logs_2026_04 USING btree (action);


--
-- Name: audit_logs_2026_04_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_04_resource_resource_id_idx ON public.audit_logs_2026_04 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_04_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_04_user_id_idx ON public.audit_logs_2026_04 USING btree (user_id);


--
-- Name: audit_logs_2026_04_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_04_workspace_id_created_at_idx ON public.audit_logs_2026_04 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_05_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_05_action_idx ON public.audit_logs_2026_05 USING btree (action);


--
-- Name: audit_logs_2026_05_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_05_resource_resource_id_idx ON public.audit_logs_2026_05 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_05_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_05_user_id_idx ON public.audit_logs_2026_05 USING btree (user_id);


--
-- Name: audit_logs_2026_05_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_05_workspace_id_created_at_idx ON public.audit_logs_2026_05 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_06_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_06_action_idx ON public.audit_logs_2026_06 USING btree (action);


--
-- Name: audit_logs_2026_06_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_06_resource_resource_id_idx ON public.audit_logs_2026_06 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_06_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_06_user_id_idx ON public.audit_logs_2026_06 USING btree (user_id);


--
-- Name: audit_logs_2026_06_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_06_workspace_id_created_at_idx ON public.audit_logs_2026_06 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_07_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_07_action_idx ON public.audit_logs_2026_07 USING btree (action);


--
-- Name: audit_logs_2026_07_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_07_resource_resource_id_idx ON public.audit_logs_2026_07 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_07_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_07_user_id_idx ON public.audit_logs_2026_07 USING btree (user_id);


--
-- Name: audit_logs_2026_07_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_07_workspace_id_created_at_idx ON public.audit_logs_2026_07 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_08_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_08_action_idx ON public.audit_logs_2026_08 USING btree (action);


--
-- Name: audit_logs_2026_08_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_08_resource_resource_id_idx ON public.audit_logs_2026_08 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_08_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_08_user_id_idx ON public.audit_logs_2026_08 USING btree (user_id);


--
-- Name: audit_logs_2026_08_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_08_workspace_id_created_at_idx ON public.audit_logs_2026_08 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_09_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_09_action_idx ON public.audit_logs_2026_09 USING btree (action);


--
-- Name: audit_logs_2026_09_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_09_resource_resource_id_idx ON public.audit_logs_2026_09 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_09_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_09_user_id_idx ON public.audit_logs_2026_09 USING btree (user_id);


--
-- Name: audit_logs_2026_09_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_09_workspace_id_created_at_idx ON public.audit_logs_2026_09 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_10_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_10_action_idx ON public.audit_logs_2026_10 USING btree (action);


--
-- Name: audit_logs_2026_10_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_10_resource_resource_id_idx ON public.audit_logs_2026_10 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_10_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_10_user_id_idx ON public.audit_logs_2026_10 USING btree (user_id);


--
-- Name: audit_logs_2026_10_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_10_workspace_id_created_at_idx ON public.audit_logs_2026_10 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_11_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_11_action_idx ON public.audit_logs_2026_11 USING btree (action);


--
-- Name: audit_logs_2026_11_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_11_resource_resource_id_idx ON public.audit_logs_2026_11 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_11_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_11_user_id_idx ON public.audit_logs_2026_11 USING btree (user_id);


--
-- Name: audit_logs_2026_11_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_11_workspace_id_created_at_idx ON public.audit_logs_2026_11 USING btree (workspace_id, created_at DESC);


--
-- Name: audit_logs_2026_12_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_12_action_idx ON public.audit_logs_2026_12 USING btree (action);


--
-- Name: audit_logs_2026_12_resource_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_12_resource_resource_id_idx ON public.audit_logs_2026_12 USING btree (resource, resource_id);


--
-- Name: audit_logs_2026_12_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_12_user_id_idx ON public.audit_logs_2026_12 USING btree (user_id);


--
-- Name: audit_logs_2026_12_workspace_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_2026_12_workspace_id_created_at_idx ON public.audit_logs_2026_12 USING btree (workspace_id, created_at DESC);


--
-- Name: idx_ai_models_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_models_provider ON public.ai_models USING btree (provider_id);


--
-- Name: idx_ai_models_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_models_type ON public.ai_models USING btree (model_type);


--
-- Name: idx_ai_models_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_models_workspace ON public.ai_models USING btree (workspace_id);


--
-- Name: idx_api_keys_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_keys_app ON public.api_keys USING btree (application_id);


--
-- Name: idx_api_keys_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_keys_hash ON public.api_keys USING btree (key_hash);


--
-- Name: idx_api_keys_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_keys_workspace ON public.api_keys USING btree (workspace_id);


--
-- Name: idx_app_versions_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_versions_app ON public.application_versions USING btree (application_id, version_number DESC);


--
-- Name: idx_app_versions_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_versions_workspace ON public.application_versions USING btree (workspace_id);


--
-- Name: idx_applications_folder; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_applications_folder ON public.applications USING btree (folder_id);


--
-- Name: idx_applications_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_applications_status ON public.applications USING btree (status);


--
-- Name: idx_applications_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_applications_type ON public.applications USING btree (type);


--
-- Name: idx_applications_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_applications_workspace ON public.applications USING btree (workspace_id);


--
-- Name: idx_cl_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cl_ws ON public.credit_ledger USING btree (workspace_id, created_at DESC);


--
-- Name: idx_conflict_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conflict_pending ON public.region_conflict_log USING btree (detected_at DESC) WHERE ((resolution)::text = 'pending'::text);


--
-- Name: idx_conflict_recent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conflict_recent ON public.region_conflict_log USING btree (detected_at DESC);


--
-- Name: idx_conversations_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_updated ON public.conversations USING btree (updated_at DESC);


--
-- Name: idx_conversations_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_user_id ON public.conversations USING btree (user_id);


--
-- Name: idx_conversations_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_workspace ON public.conversations USING btree (workspace_id);


--
-- Name: idx_data_sources_folder; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_data_sources_folder ON public.data_sources USING btree (folder_id);


--
-- Name: idx_data_sources_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_data_sources_workspace ON public.data_sources USING btree (workspace_id);


--
-- Name: idx_documents_kb_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_kb_enabled ON public.documents USING btree (knowledge_base_id, is_enabled);


--
-- Name: idx_documents_kb_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_kb_id ON public.documents USING btree (knowledge_base_id);


--
-- Name: idx_documents_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_status ON public.documents USING btree (status);


--
-- Name: idx_documents_tags_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_tags_gin ON public.documents USING gin (tags);


--
-- Name: idx_documents_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_workspace ON public.documents USING btree (workspace_id);


--
-- Name: idx_entity_folders_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_entity_folders_parent ON public.entity_folders USING btree (parent_id);


--
-- Name: idx_entity_folders_ws_kind; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_entity_folders_ws_kind ON public.entity_folders USING btree (workspace_id, entity_kind);


--
-- Name: idx_event_triggers_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_event_triggers_app ON public.event_triggers USING btree (application_id);


--
-- Name: idx_event_triggers_next; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_event_triggers_next ON public.event_triggers USING btree (next_fire_at) WHERE (enabled = true);


--
-- Name: idx_event_triggers_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_event_triggers_ws ON public.event_triggers USING btree (workspace_id);


--
-- Name: idx_idem_expire; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_idem_expire ON public.idempotency_keys USING btree (expires_at);


--
-- Name: idx_inv_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inv_ws ON public.billing_invoices USING btree (workspace_id, created_at DESC);


--
-- Name: idx_kb_folder; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kb_folder ON public.knowledge_bases USING btree (folder_id);


--
-- Name: idx_kb_folders_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kb_folders_parent ON public.kb_folders USING btree (parent_id);


--
-- Name: idx_kb_folders_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kb_folders_workspace ON public.kb_folders USING btree (workspace_id);


--
-- Name: idx_kb_grants_kb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kb_grants_kb ON public.kb_grants USING btree (kb_id);


--
-- Name: idx_kb_grants_principal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kb_grants_principal ON public.kb_grants USING btree (principal_type, principal_id);


--
-- Name: idx_kb_grants_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kb_grants_ws ON public.kb_grants USING btree (workspace_id);


--
-- Name: idx_kb_source_workflow; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kb_source_workflow ON public.knowledge_bases USING btree (source_workflow_id) WHERE (source_workflow_id IS NOT NULL);


--
-- Name: idx_knowledge_bases_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_bases_workspace ON public.knowledge_bases USING btree (workspace_id);


--
-- Name: idx_ltm_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ltm_app ON public.long_term_memories USING btree (application_id);


--
-- Name: idx_ltm_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ltm_user ON public.long_term_memories USING btree (user_id);


--
-- Name: idx_mcp_servers_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mcp_servers_ws ON public.mcp_servers USING btree (workspace_id);


--
-- Name: idx_mcp_tools_server; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mcp_tools_server ON public.mcp_tools_cache USING btree (server_id);


--
-- Name: idx_mcp_tools_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mcp_tools_ws ON public.mcp_tools_cache USING btree (workspace_id);


--
-- Name: idx_member_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_member_user ON public.workspace_member USING btree (user_id);


--
-- Name: idx_memories_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memories_app ON public.long_term_memories USING btree (application_id, created_at DESC);


--
-- Name: idx_memories_content_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memories_content_gin ON public.long_term_memories USING gin (to_tsvector('simple'::regconfig, content));


--
-- Name: idx_memories_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memories_user ON public.long_term_memories USING btree (user_id, created_at DESC);


--
-- Name: idx_memories_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memories_workspace ON public.long_term_memories USING btree (workspace_id, scope);


--
-- Name: idx_messages_conv_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_conv_id ON public.messages USING btree (conversation_id);


--
-- Name: idx_messages_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_workspace ON public.messages USING btree (workspace_id);


--
-- Name: idx_model_providers_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_model_providers_workspace ON public.model_providers USING btree (workspace_id);


--
-- Name: idx_mul_conv; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mul_conv ON public.model_usage_logs USING btree (conversation_id) WHERE (conversation_id IS NOT NULL);


--
-- Name: idx_mul_feature; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mul_feature ON public.model_usage_logs USING btree (feature) WHERE (feature IS NOT NULL);


--
-- Name: idx_outbox_due; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outbox_due ON public.webhook_outbox USING btree (next_retry_at) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_outbox_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outbox_ws ON public.webhook_outbox USING btree (workspace_id, status);


--
-- Name: idx_para_embed_kb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_para_embed_kb ON public.paragraph_embeddings USING btree (kb_id);


--
-- Name: idx_para_embed_vector; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_para_embed_vector ON public.paragraph_embeddings USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: idx_paragraph_embeddings_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_paragraph_embeddings_workspace ON public.paragraph_embeddings USING btree (workspace_id);


--
-- Name: idx_paragraphs_doc_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_paragraphs_doc_id ON public.paragraphs USING btree (document_id);


--
-- Name: idx_paragraphs_fts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_paragraphs_fts ON public.paragraphs USING gin (to_tsvector('simple'::regconfig, content));


--
-- Name: idx_paragraphs_kb_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_paragraphs_kb_id ON public.paragraphs USING btree (knowledge_base_id);


--
-- Name: idx_paragraphs_search_vector; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_paragraphs_search_vector ON public.paragraphs USING gin (search_vector);


--
-- Name: idx_paragraphs_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_paragraphs_workspace ON public.paragraphs USING btree (workspace_id);


--
-- Name: idx_project_resources_kind; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_resources_kind ON public.project_resources USING btree (kind, resource_id);


--
-- Name: idx_project_resources_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_resources_project ON public.project_resources USING btree (project_id);


--
-- Name: idx_projects_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_workspace ON public.projects USING btree (workspace_id);


--
-- Name: idx_quota_alerts_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quota_alerts_ws ON public.quota_alerts USING btree (workspace_id, enabled);


--
-- Name: idx_rating_template; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rating_template ON public.template_ratings USING btree (template_id, created_at DESC);


--
-- Name: idx_skills_folder; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_skills_folder ON public.skills USING btree (folder_id);


--
-- Name: idx_skills_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_skills_workspace ON public.skills USING btree (workspace_id);


--
-- Name: idx_sqe_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sqe_hash ON public.slow_query_explains USING btree (sql_hash, captured_at DESC);


--
-- Name: idx_sqe_recent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sqe_recent ON public.slow_query_explains USING btree (captured_at DESC);


--
-- Name: idx_template_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_template_category ON public.workspace_app_templates USING btree (category, install_count DESC) WHERE (is_public = true);


--
-- Name: idx_template_public_install; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_template_public_install ON public.workspace_app_templates USING btree (is_public, install_count DESC) WHERE (is_public = true);


--
-- Name: idx_tools_folder; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tools_folder ON public.tools USING btree (folder_id);


--
-- Name: idx_tools_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tools_workspace ON public.tools USING btree (workspace_id);


--
-- Name: idx_trigger_runs_trigger; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trigger_runs_trigger ON public.event_trigger_runs USING btree (trigger_id, fired_at DESC);


--
-- Name: idx_trigger_runs_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trigger_runs_ws ON public.event_trigger_runs USING btree (workspace_id, fired_at DESC);


--
-- Name: idx_ur_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ur_ws ON public.usage_reports USING btree (workspace_id, period_start DESC);


--
-- Name: idx_usage_logs_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_logs_app ON public.model_usage_logs USING btree (application_id);


--
-- Name: idx_usage_logs_provider_model; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_logs_provider_model ON public.model_usage_logs USING btree (provider_type, model);


--
-- Name: idx_usage_logs_workspace_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_logs_workspace_time ON public.model_usage_logs USING btree (workspace_id, created_at DESC);


--
-- Name: idx_user_quotas_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_quotas_ws ON public.user_quotas USING btree (workspace_id);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_oidc_sub; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_oidc_sub ON public.users USING btree (oidc_sub) WHERE (oidc_sub IS NOT NULL);


--
-- Name: idx_users_reset_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_reset_token ON public.users USING btree (reset_token) WHERE (reset_token IS NOT NULL);


--
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_username ON public.users USING btree (username);


--
-- Name: idx_users_verify_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_verify_token ON public.users USING btree (verify_token) WHERE (verify_token IS NOT NULL);


--
-- Name: idx_wa_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wa_pending ON public.workflow_approvals USING btree (workspace_id, status) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_wa_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wa_run ON public.workflow_approvals USING btree (run_id);


--
-- Name: idx_wf_versions_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wf_versions_app ON public.workflow_versions USING btree (application_id, version_number DESC);


--
-- Name: idx_wf_versions_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wf_versions_workspace ON public.workflow_versions USING btree (workspace_id);


--
-- Name: idx_workflow_edges_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflow_edges_workspace ON public.workflow_edges USING btree (workspace_id);


--
-- Name: idx_workflow_nodes_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflow_nodes_app ON public.workflow_nodes USING btree (application_id);


--
-- Name: idx_workflow_nodes_workspace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflow_nodes_workspace ON public.workflow_nodes USING btree (workspace_id);


--
-- Name: idx_workspace_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_workspace_slug ON public.workspace USING btree (slug) WHERE (deleted_at IS NULL);


--
-- Name: idx_wrs_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wrs_run ON public.workflow_run_steps USING btree (run_id, step_index);


--
-- Name: idx_ws_app_templates_public; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ws_app_templates_public ON public.workspace_app_templates USING btree (is_public, install_count DESC) WHERE (is_public = true);


--
-- Name: idx_ws_app_templates_ws; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ws_app_templates_ws ON public.workspace_app_templates USING btree (workspace_id, created_at DESC);


--
-- Name: idx_ws_trial_expiry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ws_trial_expiry ON public.workspace USING btree (trial_expires_at) WHERE ((trial_expires_at IS NOT NULL) AND (is_frozen = false));


--
-- Name: ix_conversations_application_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversations_application_id ON public.conversations USING btree (application_id) WHERE (application_id IS NOT NULL);


--
-- Name: ix_kb_communities_kb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kb_communities_kb ON public.kb_communities USING btree (knowledge_base_id);


--
-- Name: ix_kb_entities_kb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kb_entities_kb ON public.kb_entities USING btree (knowledge_base_id);


--
-- Name: ix_kb_entities_vec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kb_entities_vec ON public.kb_entities USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: ix_kb_mentions_para; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kb_mentions_para ON public.kb_entity_mentions USING btree (paragraph_id);


--
-- Name: ix_kb_relations_dst; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kb_relations_dst ON public.kb_relations USING btree (dst_entity_id);


--
-- Name: ix_kb_relations_src; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kb_relations_src ON public.kb_relations USING btree (src_entity_id);


--
-- Name: ix_tools_application_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tools_application_id ON public.tools USING btree (application_id) WHERE (application_id IS NOT NULL);


--
-- Name: uq_ai_models_provider_model; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_ai_models_provider_model ON public.ai_models USING btree (provider_id, model_name);


--
-- Name: uq_conversations_share_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_conversations_share_token ON public.conversations USING btree (share_token) WHERE (share_token IS NOT NULL);


--
-- Name: uq_kb_entities_norm; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_kb_entities_norm ON public.kb_entities USING btree (knowledge_base_id, norm_name, entity_type);


--
-- Name: uq_kb_relations; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_kb_relations ON public.kb_relations USING btree (knowledge_base_id, src_entity_id, dst_entity_id, relation_type);


--
-- Name: audit_logs_2026_01_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_01_action_idx;


--
-- Name: audit_logs_2026_01_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_01_pkey;


--
-- Name: audit_logs_2026_01_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_01_resource_resource_id_idx;


--
-- Name: audit_logs_2026_01_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_01_user_id_idx;


--
-- Name: audit_logs_2026_01_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_01_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_02_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_02_action_idx;


--
-- Name: audit_logs_2026_02_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_02_pkey;


--
-- Name: audit_logs_2026_02_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_02_resource_resource_id_idx;


--
-- Name: audit_logs_2026_02_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_02_user_id_idx;


--
-- Name: audit_logs_2026_02_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_02_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_03_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_03_action_idx;


--
-- Name: audit_logs_2026_03_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_03_pkey;


--
-- Name: audit_logs_2026_03_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_03_resource_resource_id_idx;


--
-- Name: audit_logs_2026_03_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_03_user_id_idx;


--
-- Name: audit_logs_2026_03_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_03_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_04_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_04_action_idx;


--
-- Name: audit_logs_2026_04_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_04_pkey;


--
-- Name: audit_logs_2026_04_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_04_resource_resource_id_idx;


--
-- Name: audit_logs_2026_04_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_04_user_id_idx;


--
-- Name: audit_logs_2026_04_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_04_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_05_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_05_action_idx;


--
-- Name: audit_logs_2026_05_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_05_pkey;


--
-- Name: audit_logs_2026_05_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_05_resource_resource_id_idx;


--
-- Name: audit_logs_2026_05_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_05_user_id_idx;


--
-- Name: audit_logs_2026_05_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_05_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_06_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_06_action_idx;


--
-- Name: audit_logs_2026_06_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_06_pkey;


--
-- Name: audit_logs_2026_06_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_06_resource_resource_id_idx;


--
-- Name: audit_logs_2026_06_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_06_user_id_idx;


--
-- Name: audit_logs_2026_06_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_06_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_07_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_07_action_idx;


--
-- Name: audit_logs_2026_07_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_07_pkey;


--
-- Name: audit_logs_2026_07_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_07_resource_resource_id_idx;


--
-- Name: audit_logs_2026_07_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_07_user_id_idx;


--
-- Name: audit_logs_2026_07_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_07_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_08_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_08_action_idx;


--
-- Name: audit_logs_2026_08_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_08_pkey;


--
-- Name: audit_logs_2026_08_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_08_resource_resource_id_idx;


--
-- Name: audit_logs_2026_08_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_08_user_id_idx;


--
-- Name: audit_logs_2026_08_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_08_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_09_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_09_action_idx;


--
-- Name: audit_logs_2026_09_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_09_pkey;


--
-- Name: audit_logs_2026_09_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_09_resource_resource_id_idx;


--
-- Name: audit_logs_2026_09_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_09_user_id_idx;


--
-- Name: audit_logs_2026_09_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_09_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_10_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_10_action_idx;


--
-- Name: audit_logs_2026_10_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_10_pkey;


--
-- Name: audit_logs_2026_10_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_10_resource_resource_id_idx;


--
-- Name: audit_logs_2026_10_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_10_user_id_idx;


--
-- Name: audit_logs_2026_10_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_10_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_11_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_11_action_idx;


--
-- Name: audit_logs_2026_11_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_11_pkey;


--
-- Name: audit_logs_2026_11_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_11_resource_resource_id_idx;


--
-- Name: audit_logs_2026_11_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_11_user_id_idx;


--
-- Name: audit_logs_2026_11_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_11_workspace_id_created_at_idx;


--
-- Name: audit_logs_2026_12_action_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_action ATTACH PARTITION public.audit_logs_2026_12_action_idx;


--
-- Name: audit_logs_2026_12_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.audit_logs_pkey ATTACH PARTITION public.audit_logs_2026_12_pkey;


--
-- Name: audit_logs_2026_12_resource_resource_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_resource ATTACH PARTITION public.audit_logs_2026_12_resource_resource_id_idx;


--
-- Name: audit_logs_2026_12_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_user ATTACH PARTITION public.audit_logs_2026_12_user_id_idx;


--
-- Name: audit_logs_2026_12_workspace_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_audit_logs_ws_created ATTACH PARTITION public.audit_logs_2026_12_workspace_id_created_at_idx;


--
-- Name: ai_models ai_models_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_models
    ADD CONSTRAINT ai_models_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.model_providers(id) ON DELETE CASCADE;


--
-- Name: ai_models ai_models_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_models
    ADD CONSTRAINT ai_models_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: api_keys api_keys_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: applications applications_llm_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_llm_model_id_fkey FOREIGN KEY (llm_model_id) REFERENCES public.ai_models(id) ON DELETE SET NULL;


--
-- Name: applications applications_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: documents documents_knowledge_base_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_knowledge_base_id_fkey FOREIGN KEY (knowledge_base_id) REFERENCES public.knowledge_bases(id) ON DELETE CASCADE;


--
-- Name: documents documents_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: kb_entity_mentions kb_entity_mentions_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_entity_mentions
    ADD CONSTRAINT kb_entity_mentions_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES public.kb_entities(id) ON DELETE CASCADE;


--
-- Name: kb_entity_mentions kb_entity_mentions_paragraph_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_entity_mentions
    ADD CONSTRAINT kb_entity_mentions_paragraph_id_fkey FOREIGN KEY (paragraph_id) REFERENCES public.paragraphs(id) ON DELETE CASCADE;


--
-- Name: kb_relation_mentions kb_relation_mentions_paragraph_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_relation_mentions
    ADD CONSTRAINT kb_relation_mentions_paragraph_id_fkey FOREIGN KEY (paragraph_id) REFERENCES public.paragraphs(id) ON DELETE CASCADE;


--
-- Name: kb_relation_mentions kb_relation_mentions_relation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_relation_mentions
    ADD CONSTRAINT kb_relation_mentions_relation_id_fkey FOREIGN KEY (relation_id) REFERENCES public.kb_relations(id) ON DELETE CASCADE;


--
-- Name: kb_relations kb_relations_dst_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_relations
    ADD CONSTRAINT kb_relations_dst_entity_id_fkey FOREIGN KEY (dst_entity_id) REFERENCES public.kb_entities(id) ON DELETE CASCADE;


--
-- Name: kb_relations kb_relations_src_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kb_relations
    ADD CONSTRAINT kb_relations_src_entity_id_fkey FOREIGN KEY (src_entity_id) REFERENCES public.kb_entities(id) ON DELETE CASCADE;


--
-- Name: knowledge_bases knowledge_bases_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_bases
    ADD CONSTRAINT knowledge_bases_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: long_term_memories long_term_memories_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.long_term_memories
    ADD CONSTRAINT long_term_memories_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: messages messages_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: model_providers model_providers_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_providers
    ADD CONSTRAINT model_providers_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: paragraph_embeddings paragraph_embeddings_paragraph_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paragraph_embeddings
    ADD CONSTRAINT paragraph_embeddings_paragraph_id_fkey FOREIGN KEY (paragraph_id) REFERENCES public.paragraphs(id) ON DELETE CASCADE;


--
-- Name: paragraph_embeddings paragraph_embeddings_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paragraph_embeddings
    ADD CONSTRAINT paragraph_embeddings_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: paragraphs paragraphs_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paragraphs
    ADD CONSTRAINT paragraphs_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: paragraphs paragraphs_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paragraphs
    ADD CONSTRAINT paragraphs_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: triggers triggers_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triggers
    ADD CONSTRAINT triggers_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: workflow_edges workflow_edges_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_edges
    ADD CONSTRAINT workflow_edges_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: workflow_nodes workflow_nodes_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_nodes
    ADD CONSTRAINT workflow_nodes_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: workspace_member workspace_member_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_member
    ADD CONSTRAINT workspace_member_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: workspace_member workspace_member_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_member
    ADD CONSTRAINT workspace_member_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspace(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict RiWRDyAsmeaIgD3kCMzNXm5mwZonBIkVKqTqwASmxSXgT8Bo5sggNWtSwqAXRRc


-- ═══ Bootstrap 種子資料 ═══
--
-- PostgreSQL database dump
--

\restrict NuSrHlQ39WONZhVHxmVuTG7xk6mnZ0qf1rG7aao1VK2w841elBU6el3pBkMda36

-- Dumped from database version 16.13 (Debian 16.13-1.pgdg12+1)
-- Dumped by pg_dump version 16.13 (Debian 16.13-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: system_settings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.system_settings (key, value, description, updated_at, updated_by) FROM stdin;
embedding.default_model	"snowflake-arctic-embed2"	Default embedding model	2026-05-18 23:58:33.502484+08	\N
embedding.dimension	1024	Embedding vector dimension	2026-05-18 23:58:33.502484+08	\N
reranker.default_type	"cross_encoder"	Default reranker (cohere/ollama/cross_encoder/http)	2026-05-18 23:58:33.502484+08	\N
search.rrf_default_vector_weight	0.7	Hybrid search vector weight (0-1)	2026-05-18 23:58:33.502484+08	\N
search.default_top_k	5	Default top_k for retrieval	2026-05-18 23:58:33.502484+08	\N
upload.max_file_size_mb	50	Max upload size (MB)	2026-05-18 23:58:33.502484+08	\N
security.password_min_length	8	Min password length	2026-05-18 23:58:33.502484+08	\N
security.login_lockout_threshold	5	Failed login attempts before captcha	2026-05-18 23:58:33.502484+08	\N
security.session_timeout_minutes	60	Session idle timeout (minutes)	2026-05-18 23:58:33.502484+08	\N
embedding.active	{"dim": 1024, "model": "snowflake-arctic-embed2", "api_key": "dummy", "base_url": "http://embedder:11434/v1"}	\N	2026-05-26 03:26:47.749802+08	\N
upload.allowed_extensions	["pdf", "docx", "doc", "md", "txt", "csv", "html", "xlsx", "xls", "png", "jpg", "jpeg", "webp", "tiff", "bmp"]	Allowed extensions	2026-05-18 23:58:33.502484+08	\N
embedding.reindex	{"done": 3806, "model": "bge-m3", "total": 3806, "status": "done", "entities": 165, "migrated": true, "started_at": "2026-05-25T19:26:47.083458", "target_dim": 1024, "finished_at": "2026-05-25T19:56:38.312898"}	\N	2026-05-26 03:56:38.313259+08	\N
default.llm	"gemma4:e4b"	\N	2026-05-23 09:12:09.299798+08	cf4633da-9d2c-453b-a198-218031b17f96
default.embedding	""	\N	2026-05-23 09:12:09.313356+08	cf4633da-9d2c-453b-a198-218031b17f96
default.vision	"glm-ocr:bf16"	\N	2026-05-23 09:12:09.328697+08	cf4633da-9d2c-453b-a198-218031b17f96
default.stt	""	\N	2026-05-23 09:12:09.340155+08	cf4633da-9d2c-453b-a198-218031b17f96
default.tts	""	\N	2026-05-23 09:12:09.362928+08	cf4633da-9d2c-453b-a198-218031b17f96
default.rerank	""	\N	2026-05-23 09:12:09.351769+08	cf4633da-9d2c-453b-a198-218031b17f96
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, username, email, display_name, password_hash, ldap_dn, status, roles, department, tenant_id, is_superuser, avatar_url, created_at, updated_at, created_by, updated_by, oidc_sub, oidc_issuer, email_verified_at, verify_token, verify_token_exp, reset_token, reset_token_exp, allowed_login_methods) FROM stdin;
cf4633da-9d2c-453b-a198-218031b17f96	admin	\N	系統管理員	$2b$12$G6QzMyJa/htFRTBxqWoL5.g8mHheep4qQgJbbRS2MFSEUIrhzwiU2	\N	active	{admin,user}	\N	\N	t	\N	2026-05-14 23:09:19.558819+08	2026-05-14 23:09:19.558819+08	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: workspace; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.workspace (id, name, slug, description, plan, quota_meta, created_at, updated_at, deleted_at, trial_expires_at, trial_plan, is_frozen, signup_email, signup_source, primary_region) FROM stdin;
00000000-0000-0000-0000-000000000001	Default	default	初次安裝預設工作區，收容遷移前的所有舊資料	free	{}	2026-05-15 21:56:54.456873+08	2026-05-15 21:56:54.456873+08	\N	\N	\N	f	\N	\N	default
a5e158e3-9a09-43cb-a3e6-a546e635b884	工程部	engineering	\N	free	{}	2026-05-15 21:58:46.687696+08	2026-05-15 21:58:46.846961+08	2026-05-15 21:58:46.84862+08	\N	\N	f	\N	\N	default
\.


--
-- Data for Name: workspace_member; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.workspace_member (id, workspace_id, user_id, role, invited_by, invited_at, joined_at, is_active) FROM stdin;
8c161a73-29a0-400c-9bf1-5e16dc17af56	00000000-0000-0000-0000-000000000001	cf4633da-9d2c-453b-a198-218031b17f96	owner	\N	2026-05-15 21:56:54.457402+08	2026-05-15 21:56:54.457402+08	t
5c7915e4-1e03-40d7-a2cb-e4860e943a10	a5e158e3-9a09-43cb-a3e6-a546e635b884	cf4633da-9d2c-453b-a198-218031b17f96	owner	\N	2026-05-15 21:58:46.687696+08	2026-05-15 21:58:46.693448+08	t
\.


--
-- PostgreSQL database dump complete
--

\unrestrict NuSrHlQ39WONZhVHxmVuTG7xk6mnZ0qf1rG7aao1VK2w841elBU6el3pBkMda36

--
-- v5.12 post-init（銷售交付）：首次登入強制改密
--   出廠預設 admin 密碼為已知值（部署文件公開）→ 標記強制首登改密，
--   降低「客戶忘了改、預設帳密被人登入」風險。idempotent，重跑安全。
--
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS must_change_password boolean DEFAULT false NOT NULL;
UPDATE public.users SET must_change_password = true WHERE username = 'admin';

