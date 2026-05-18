"""app — list / install starter-pack / export / import."""
from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from ..api import client

console = Console()


@click.group("app")
def app_group() -> None:
    """Application management (v4.4 D — supplements legacy `apps` group)."""


@app_group.command("list")
def app_list() -> None:
    with client() as c:
        r = c.get("/api/v1/applications")
        r.raise_for_status()
        items = (r.json() or {}).get("data", []) or []
    t = Table(title=f"Applications ({len(items)})")
    for col in ("id", "name", "type", "status"):
        t.add_column(col)
    for a in items:
        t.add_row(str(a.get("id", ""))[:8], a.get("name", ""), a.get("type", ""), a.get("status", ""))
    console.print(t)


@app_group.command("install")
@click.argument("source")  # e.g. starter-pack
@click.argument("pack_id")
def install(source: str, pack_id: str) -> None:
    """Install an application from starter-pack."""
    if source != "starter-pack":
        raise click.ClickException(f"only 'starter-pack' source supported (got {source!r})")
    with client() as c:
        r = c.post("/api/v1/applications/install", json={"source": source, "pack_id": pack_id})
        r.raise_for_status()
        data = (r.json() or {}).get("data") or {}
    click.echo(f"OK  installed {pack_id} -> app id={data.get('id')}")


@app_group.command("export")
@click.argument("app_id")
def export(app_id: str) -> None:
    """Export application config as JSON to stdout."""
    with client() as c:
        r = c.get(f"/api/v1/applications/{app_id}/export")
        r.raise_for_status()
    sys.stdout.write(json.dumps(r.json(), ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


@app_group.command("import")
@click.argument("file", type=click.File("r"))
def import_app(file) -> None:
    """Import application config from JSON file (use '-' for stdin)."""
    payload = json.load(file)
    with client() as c:
        r = c.post("/api/v1/applications/import", json=payload)
        r.raise_for_status()
        data = (r.json() or {}).get("data") or {}
    click.echo(f"OK  imported app id={data.get('id')}")


# TODO (v4.5): clone / fork / version diff
