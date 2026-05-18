"""Seed 5 example public templates — v4.10 J.

手動跑（dev 環境 admin token）：

    python3 tools/seed-marketplace.py \
        --base http://localhost \
        --token <admin_jwt> \
        --workspace <ws_id>

注意：實際呼叫的是 v2.5 workspace-scoped `POST /app-templates` API，
帶 `is_public=true` 與 v4.10 J 的 marketplace metadata。
這份檔案目前是 placeholder：請依需求填 schema_json。
"""
import argparse
import asyncio
import httpx


EXAMPLES = [
    {
        "name": "HR 助理（公開版）",
        "description": "請假 / 報帳 / onboarding QA — 來自 staffKM 官方範本",
        "category": "hr",
        "tags": ["hr", "qa", "knowledge"],
        "is_public": True,
        "publisher_name": "staffKM team",
        "verified": True,
        "schema_json": {"_placeholder": "請貼上 starter pack 01-hr-assistant.json 內容"},
    },
    {
        "name": "Sales 開發信生成器",
        "description": "輸入 lead 公司名 → 自動產出 3 版冷開發信",
        "category": "sales",
        "tags": ["sales", "outreach"],
        "is_public": True,
        "publisher_name": "staffKM team",
        "verified": True,
        "schema_json": {"_placeholder": "todo"},
    },
    {
        "name": "工程 PR Review 助手",
        "description": "貼上 diff → 自動列風險點 + 建議",
        "category": "engineering",
        "tags": ["dev", "code-review"],
        "is_public": True,
        "publisher_name": "staffKM team",
        "verified": True,
        "schema_json": {"_placeholder": "todo"},
    },
    {
        "name": "客服 FAQ 自動回答",
        "description": "綁定 KB → 從常見問答自動產覆",
        "category": "support",
        "tags": ["support", "qa", "knowledge"],
        "is_public": True,
        "publisher_name": "staffKM team",
        "verified": True,
        "schema_json": {"_placeholder": "todo"},
    },
    {
        "name": "會議記錄摘要",
        "description": "貼上逐字稿 → 重點 / TODO / 決議 三段式摘要",
        "category": "productivity",
        "tags": ["meeting", "summary"],
        "is_public": True,
        "publisher_name": "staffKM team",
        "verified": True,
        "schema_json": {"_placeholder": "todo"},
    },
]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base",      required=True, help="gateway base URL, e.g. http://localhost")
    parser.add_argument("--token",     required=True, help="JWT")
    parser.add_argument("--workspace", required=True, help="workspace UUID")
    args = parser.parse_args()

    headers = {
        "Authorization": f"Bearer {args.token}",
        "X-Workspace-ID": args.workspace,
    }
    async with httpx.AsyncClient(headers=headers, timeout=30) as c:
        for e in EXAMPLES:
            r = await c.post(f"{args.base}/api/v1/app-templates", json=e)
            print(r.status_code, e["name"], "—", r.text[:160])


if __name__ == "__main__":
    asyncio.run(main())
