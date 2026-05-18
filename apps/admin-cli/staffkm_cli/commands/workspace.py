"""workspace — list / create / delete / switch."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..api import client
from ..config import load_credentials, save_credentials

console = Console()


@click.group("workspace")
def workspace_group() -> None:
    """Manage workspaces."""


@workspace_group.command("list")
def list_workspaces() -> None:
    with client() as c:
        r = c.get("/api/v1/workspaces")
        r.raise_for_status()
        data = (r.json() or {}).get("data", []) or []
    t = Table(title=f"Workspaces ({len(data)})")
    t.add_column("ID"); t.add_column("Name"); t.add_column("Created")
    for w in data:
        t.add_row(str(w.get("id", ""))[:8], w.get("name", ""), str(w.get("created_at", ""))[:10])
    console.print(t)


@workspace_group.command("create")
@click.argument("name")
def create(name: str) -> None:
    with client() as c:
        r = c.post("/api/v1/workspaces", json={"name": name})
        r.raise_for_status()
        data = (r.json() or {}).get("data") or {}
    click.echo(f"OK  created workspace id={data.get('id')} name={data.get('name')}")


@workspace_group.command("delete")
@click.argument("workspace_id")
@click.confirmation_option(prompt="confirm delete workspace?")
def delete(workspace_id: str) -> None:
    with client() as c:
        r = c.delete(f"/api/v1/workspaces/{workspace_id}")
        r.raise_for_status()
    click.echo(f"OK  deleted workspace {workspace_id}")


@workspace_group.command("switch")
@click.argument("workspace_id")
def switch(workspace_id: str) -> None:
    """Set current workspace_id (saved to credentials)."""
    cred = load_credentials()
    if not cred:
        raise click.ClickException("not logged in")
    save_credentials(cred["base"], cred["token"], workspace_id=workspace_id)
    click.echo(f"OK  switched to workspace {workspace_id[:8]}")
