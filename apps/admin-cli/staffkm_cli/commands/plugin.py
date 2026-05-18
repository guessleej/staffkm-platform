"""plugin — list / reload (v4.3 Theme C plugin SDK)."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..api import client

console = Console()


@click.group("plugin")
def plugin_group() -> None:
    """Plugin SDK admin commands (interfaces v4.3 Theme C)."""


@plugin_group.command("list")
def plugin_list() -> None:
    with client() as c:
        r = c.get("/api/v1/admin/plugins")
        r.raise_for_status()
        items = (r.json() or {}).get("data", []) or []
    t = Table(title=f"Loaded plugins ({len(items)})")
    for col in ("name", "version", "nodes", "providers", "hooks"):
        t.add_column(col)
    for p in items:
        t.add_row(
            p.get("name", ""),
            p.get("version", ""),
            str(len(p.get("nodes", []) or [])),
            str(len(p.get("providers", []) or [])),
            str(len(p.get("hooks", []) or [])),
        )
    console.print(t)


@plugin_group.command("reload")
def plugin_reload() -> None:
    with client() as c:
        r = c.post("/api/v1/admin/plugins/reload")
        r.raise_for_status()
        data = (r.json() or {}).get("data") or {}
    click.echo(f"OK  reloaded plugins: count={data.get('count', '?')}")


# TODO (v4.5): plugin install from git URL / enable / disable
