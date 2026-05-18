"""Seed eval KB — 把 seed_corpus/*.md 上傳到指定 workspace，印出每段 paragraph_id。

usage:
    python tools/eval/seed_eval_kb.py \\
        --base http://localhost \\
        --token <JWT> \\
        --workspace-id <UUID> \\
        --kb-name staffkm-eval-kb \\
        --output tools/eval/seeded_paragraphs.json

輸出 seeded_paragraphs.json 結構：
{
  "kb_id": "...",
  "documents": [
    {"file": "01-leave-policy.md", "doc_id": "...", "paragraphs": [
      {"id": "...", "content": "...", "title": "年假"}, ...
    ]},
    ...
  ]
}

然後 rag_eval.py 透過 --seeded 參數讀此檔，把 dataset 內每條 query 的
expected_corpus_anchors (file + title_contains) 解析成實際 paragraph_id。

TODO（使用者請依實際 backend route 微調）：
- KB create / upload / list-paragraphs 路徑沿用 v3.x 慣例 `/api/v1/knowledge/kbs`，
  若實際以 workspace-scoped 形式註冊（如 `/api/v1/workspaces/{ws}/knowledge/kbs`），
  請在 ENDPOINT_* 常數調整。
- 不同部署 embedding 速度差異大；POLL_INTERVAL / POLL_MAX_ROUNDS 可調。
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import httpx


ENDPOINT_KB_CREATE = "/api/v1/knowledge/kbs"
ENDPOINT_KB_UPLOAD = "/api/v1/knowledge/kbs/{kb_id}/documents"
ENDPOINT_DOC_PARAGRAPHS = "/api/v1/knowledge/kbs/{kb_id}/documents/{doc_id}/paragraphs"

POLL_INTERVAL = 3  # seconds
POLL_MAX_ROUNDS = 20  # 60s 最大等候 / doc


async def _wait_paragraphs(
    client: httpx.AsyncClient, base: str, kb_id: str, doc_id: str
) -> list[dict]:
    """Poll 直到 paragraphs 出現（embedding 完成）。"""
    url = base + ENDPOINT_DOC_PARAGRAPHS.format(kb_id=kb_id, doc_id=doc_id)
    for _ in range(POLL_MAX_ROUNDS):
        r = await client.get(url)
        r.raise_for_status()
        items = r.json().get("data", {}).get("items", [])
        if items:
            return items
        await asyncio.sleep(POLL_INTERVAL)
    return []


async def upload_kb(
    base: str, token: str, ws_id: str, kb_name: str, corpus_dir: str
) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": ws_id,
    }
    async with httpx.AsyncClient(timeout=120, headers=headers) as client:
        # 1. create KB
        r = await client.post(
            base + ENDPOINT_KB_CREATE,
            json={"name": kb_name, "description": "v3.4 P4 eval seed"},
        )
        r.raise_for_status()
        kb_id = r.json()["data"]["id"]

        documents = []
        for md_file in sorted(Path(corpus_dir).glob("*.md")):
            print(f"[upload] {md_file.name}")
            with open(md_file, "rb") as f:
                files = {"file": (md_file.name, f, "text/markdown")}
                r = await client.post(
                    base + ENDPOINT_KB_UPLOAD.format(kb_id=kb_id),
                    files=files,
                )
                r.raise_for_status()
                doc_id = r.json()["data"]["id"]

            items = await _wait_paragraphs(client, base, kb_id, doc_id)
            if not items:
                print(f"[warn] no paragraphs for {md_file.name} after polling")

            paragraphs = [
                {
                    "id": p["id"],
                    "content": (p.get("content") or "")[:120],
                    "title": p.get("title") or "",
                }
                for p in items
            ]
            documents.append(
                {"file": md_file.name, "doc_id": doc_id, "paragraphs": paragraphs}
            )

        return {"kb_id": kb_id, "documents": documents}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--kb-name", default="staffkm-eval-kb")
    parser.add_argument("--corpus-dir", default="tools/eval/seed_corpus")
    parser.add_argument("--output", default="tools/eval/seeded_paragraphs.json")
    args = parser.parse_args()

    result = await upload_kb(
        args.base, args.token, args.workspace_id, args.kb_name, args.corpus_dir
    )
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total = sum(len(d["paragraphs"]) for d in result["documents"])
    print(
        f"Seeded KB {result['kb_id']} — {len(result['documents'])} docs / "
        f"{total} paragraphs"
    )
    print(f"Output → {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
