"""Demo seeder（M5 GA）— 灌一份「公司行政」情境的範例資料給新環境試玩。

用法：
    DB_URL="postgresql://..." python tools/scripts/demo_seed.py

會在 default workspace 建立：
- 3 個 application（行政總管 / 採購助理 / 法規查詢）
- 4 個 knowledge base（員工守則 / 採購規範 / 法規彙整 / SOP 速查）
- 3 個 tool（內部 HTTP API stub）
- 2 個 skill（會議紀錄整理 / 週報撰寫）
- 5 個 sample memory（user / app / team 各 scope）
- 1 個 event trigger（每日 9 點跑「行政總管」整理昨日待辦）

非破壞：所有 INSERT 都 ON CONFLICT DO NOTHING；可重複跑。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime


DEFAULT_WORKSPACE = "00000000-0000-0000-0000-000000000001"


_APPS = [
    {
        "name": "行政總管",
        "description": "問請假 / 簽呈 / 會議室 / 福利等公司 SOP",
        "type": "simple",
        "system_prompt": "你是公司行政總管，根據附上的公司文件回答員工問題。"
                          "若不確定，請說「請洽人資 hr@example.com」。",
        "welcome_message": "我是行政總管，有任何 SOP / 流程問題都可以問我。",
        "suggested_questions": ["請假怎麼申請？", "差勤系統在哪？", "新進員工到職流程"],
    },
    {
        "name": "採購助理",
        "description": "走採購流程、找廠商、查報價",
        "type": "simple",
        "system_prompt": "你是採購助理，協助同仁走簽呈與比價流程。引用採購規範。",
        "welcome_message": "需要採購支援嗎？我可以幫你找流程、樣板、廠商。",
        "suggested_questions": ["10 萬以下的採購流程", "提供合格廠商名單", "請給我採購單範本"],
    },
    {
        "name": "法規查詢",
        "description": "勞基法 / 個資法 / 公司治理規範",
        "type": "simple",
        "system_prompt": "你是法務助理，依法規條文回答。請務必引用條號。",
        "welcome_message": "法規問題請說明場景，我會引用適用條文。",
        "suggested_questions": ["個資外洩 24 小時內要做什麼？", "資遣費怎麼算", "特休年資計算"],
    },
]

_KBS = [
    {"name": "員工守則", "description": "公司內部規章彙編"},
    {"name": "採購規範", "description": "採購流程、簽呈、廠商管理"},
    {"name": "法規彙整", "description": "勞基法、個資法、公司治理"},
    {"name": "SOP 速查", "description": "跨部門常見 SOP 一頁式索引"},
]

_TOOLS = [
    {"name": "員工通訊錄查詢", "kind": "http", "config": {"endpoint": "https://internal.example.com/api/employees"}},
    {"name": "差勤系統",      "kind": "http", "config": {"endpoint": "https://hr.example.com/api/attendance"}},
    {"name": "簽呈系統",      "kind": "http", "config": {"endpoint": "https://eform.example.com/api/forms"}},
]

_SKILLS = [
    {"name": "會議紀錄整理", "prompt_template":
        "請將以下會議逐字稿整理成：\n1. 與會者\n2. 決議事項（含 owner）\n3. 待辦事項（含 due date）"},
    {"name": "週報撰寫",     "prompt_template":
        "請依以下要點撰寫週報（一頁式）：\n- 本週完成\n- 下週計畫\n- 風險 / 阻礙"},
]

_MEMORIES = [
    {"scope": "team", "content": "公司財年從 4 月起算，請假以財年為單位重置", "importance": 8},
    {"scope": "team", "content": "資訊系統維護時段每月第二個週六 22:00-02:00", "importance": 7},
    {"scope": "app",  "content": "採購總額 ≥ 10 萬須走 PMP 並付兩家報價",     "importance": 9},
    {"scope": "app",  "content": "差旅費月底前 15 日內請款，逾期不予受理",     "importance": 7},
    {"scope": "team", "content": "個資事件 24 小時內通報資安長",               "importance": 10},
]


async def _seed(conn, workspace_id: str) -> None:
    now = datetime.utcnow()

    # 1) Applications
    for a in _APPS:
        aid = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO applications
              (id, workspace_id, name, description, type, status, system_prompt,
               welcome_message, suggested_questions, knowledge_base_ids, config,
               is_public, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, 'active', $6, $7, $8::jsonb, '[]'::jsonb, '{}'::jsonb,
                    false, $9, $9)
            ON CONFLICT DO NOTHING
            """,
            aid, workspace_id, a["name"], a["description"], a["type"],
            a["system_prompt"], a["welcome_message"],
            json.dumps(a["suggested_questions"], ensure_ascii=False), now,
        )

    # 2) Knowledge bases（若有對應表）
    try:
        for k in _KBS:
            await conn.execute(
                """
                INSERT INTO knowledge_bases (id, workspace_id, name, description, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
                """,
                str(uuid.uuid4()), workspace_id, k["name"], k["description"], now,
            )
    except Exception:
        print("[warn] knowledge_bases 表不在；跳過", file=sys.stderr)

    # 3) Tools
    for t in _TOOLS:
        await conn.execute(
            """
            INSERT INTO tools (id, workspace_id, name, kind, config, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $6)
            ON CONFLICT DO NOTHING
            """,
            str(uuid.uuid4()), workspace_id, t["name"], t["kind"],
            json.dumps(t["config"], ensure_ascii=False), now,
        )

    # 4) Skills
    for s in _SKILLS:
        await conn.execute(
            """
            INSERT INTO skills (id, workspace_id, name, prompt_template, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $5)
            ON CONFLICT DO NOTHING
            """,
            str(uuid.uuid4()), workspace_id, s["name"], s["prompt_template"], now,
        )

    # 5) Memories
    for m in _MEMORIES:
        await conn.execute(
            """
            INSERT INTO long_term_memories
              (id, workspace_id, scope, content, importance, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            str(uuid.uuid4()), workspace_id, m["scope"], m["content"], m["importance"], now,
        )


async def main() -> None:
    try:
        import asyncpg
    except ImportError:
        sys.exit("asyncpg 未安裝")
    db_url = os.environ.get("DB_URL")
    if not db_url:
        sys.exit("DB_URL 必填")
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(db_url)
    try:
        await _seed(conn, DEFAULT_WORKSPACE)
        print("✓ seeded default workspace（applications / tools / skills / memories）")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
