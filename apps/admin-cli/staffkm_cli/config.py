"""Config storage — ~/.staffkm/credentials.json (v4.4 D)."""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".staffkm"
CRED_FILE = CONFIG_DIR / "credentials.json"


def save_credentials(base: str, token: str, workspace_id: str | None = None) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CRED_FILE.write_text(json.dumps({
        "base": base.rstrip("/"),
        "token": token,
        "workspace_id": workspace_id,
    }))
    try:
        os.chmod(CRED_FILE, 0o600)
    except OSError:
        pass


def load_credentials() -> dict | None:
    if not CRED_FILE.exists():
        return None
    try:
        return json.loads(CRED_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def clear_credentials() -> None:
    if CRED_FILE.exists():
        CRED_FILE.unlink()


def get_or_die() -> dict:
    """Return credentials or raise ClickException (lazy import click)."""
    cred = load_credentials()
    if not cred:
        import click
        raise click.ClickException(
            "not logged in. Run: staffkm-cli login --base <URL> --email <EMAIL> --password <PW>"
        )
    return cred
