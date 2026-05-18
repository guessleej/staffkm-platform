"""Bulk-evaluate prompts against an application and dump JSONL results."""
from __future__ import annotations

import json
import os
import sys
from staffkm import StaffKM


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: bulk_eval.py <app_id> <prompts.txt>")
        sys.exit(1)
    app_id, prompts_path = sys.argv[1], sys.argv[2]

    client = StaffKM(
        base_url=os.environ["BASE_URL"],
        api_key=os.environ["API_KEY"],
        workspace_id=os.environ.get("WORKSPACE_ID"),
    )
    with open(prompts_path, encoding="utf-8") as fh:
        prompts = [line.strip() for line in fh if line.strip()]

    for p in prompts:
        try:
            res = client.chat.send(application_id=app_id, message=p)
            print(json.dumps({"prompt": p, "response": res}, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"prompt": p, "error": str(e)}, ensure_ascii=False))
    client.close()


if __name__ == "__main__":
    main()
