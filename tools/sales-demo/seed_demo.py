"""Sales demo seeder — v4.1 A。

usage:
    python tools/sales-demo/seed_demo.py --base http://localhost --token <ADMIN_JWT>

流程：
1. trial signup → 建 "StaffKM Demo" workspace + demo@staffkm.example.com 帳號
2. （可選）後續：login 拿 ws-scoped token → install 全部 5 個 starter pack →
   上傳 sample docs。完整自動化請看 demo-script.md。

簡化版只跑 signup；其餘步驟人工 / admin UI 操作。
"""
from __future__ import annotations
import argparse
import asyncio

import httpx


DEMO_EMAIL = "demo@staffkm.example.com"
DEMO_PASSWORD = "DemoStaffKM2026!"
DEMO_WORKSPACE = "StaffKM Demo"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="e.g. http://localhost")
    parser.add_argument("--token", required=False, default="",
                        help="admin JWT (only needed for starter-pack auto-install)")
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=60) as c:
        # 1. trial signup
        r = await c.post(f"{args.base}/api/v1/auth/trial", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
            "workspace_name": DEMO_WORKSPACE,
        })
        if r.status_code == 409:
            print(f"[demo] {DEMO_EMAIL} already exists — skipping signup")
        else:
            r.raise_for_status()
            print(f"[demo] signup OK: {r.json()}")

        # 2. starter pack install（若提供 admin token + 已知 workspace_id）
        if args.token:
            print("[demo] starter-pack install — admin token detected but ws-scoped install "
                  "requires login flow; see demo-script.md")

    print(f"\n[demo] done. login: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
