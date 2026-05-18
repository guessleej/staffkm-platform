"""Upload a single document into a knowledge base."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from staffkm import StaffKM


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: upload_doc.py <kb_id> <file_path>")
        sys.exit(1)
    kb_id, path = sys.argv[1], Path(sys.argv[2])

    client = StaffKM(
        base_url=os.environ["BASE_URL"],
        api_key=os.environ["API_KEY"],
        workspace_id=os.environ.get("WORKSPACE_ID"),
    )
    with path.open("rb") as fh:
        res = client.knowledge.docs.upload(kb_id=kb_id, file=fh, filename=path.name)
    print(res)
    client.close()


if __name__ == "__main__":
    main()
