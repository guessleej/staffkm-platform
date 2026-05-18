"""Stream tokens from a chat application.

Usage:
    BASE_URL=http://localhost API_KEY=sk_xxx WORKSPACE_ID=ws_abc APP_ID=app_123 \
        python chat_streaming.py
"""
from __future__ import annotations

import os
from staffkm import StaffKM


def main() -> None:
    client = StaffKM(
        base_url=os.environ["BASE_URL"],
        api_key=os.environ["API_KEY"],
        workspace_id=os.environ.get("WORKSPACE_ID"),
    )
    app_id = os.environ["APP_ID"]
    prompt = "用一句話介紹 staffKM。"
    print(f"> {prompt}\n")
    for tok in client.chat.stream(application_id=app_id, message=prompt):
        print(tok, end="", flush=True)
    print()
    client.close()


if __name__ == "__main__":
    main()
