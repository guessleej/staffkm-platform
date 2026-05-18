"""user — list / invite / quota set."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..api import client

console = Console()


@click.group("user")
def user_group() -> None:
    """User management."""


@user_group.command("list")
def user_list() -> None:
    with client() as c:
        r = c.get("/api/v1/users")
        r.raise_for_status()
        items = (r.json() or {}).get("data", []) or []
    t = Table(title=f"Users ({len(items)})")
    for col in ("id", "email", "role", "status"):
        t.add_column(col)
    for u in items:
        t.add_row(str(u.get("id", ""))[:8], u.get("email", ""), u.get("role", ""), u.get("status", ""))
    console.print(t)


@user_group.command("invite")
@click.argument("email")
@click.option("--role", default="member", type=click.Choice(["admin", "member", "viewer"]))
def invite(email: str, role: str) -> None:
    with client() as c:
        r = c.post("/api/v1/users/invite", json={"email": email, "role": role})
        r.raise_for_status()
    click.echo(f"OK  invited {email} as {role}")


@user_group.group("quota")
def quota_group() -> None:
    """Per-user quota."""


@quota_group.command("set")
@click.argument("user_id")
@click.option("--tokens", type=int, default=None, help="monthly token cap")
@click.option("--cost", type=float, default=None, help="monthly cost cap USD")
def quota_set(user_id: str, tokens: int | None, cost: float | None) -> None:
    payload: dict = {}
    if tokens is not None:
        payload["monthly_token_cap"] = tokens
    if cost is not None:
        payload["monthly_cost_cap_usd"] = cost
    if not payload:
        raise click.UsageError("at least one of --tokens / --cost required")
    with client() as c:
        r = c.put(f"/api/v1/users/{user_id}/quota", json=payload)
        r.raise_for_status()
    click.echo(f"OK  quota updated for user {user_id[:8]} -> {payload}")


# TODO (v4.5): user disable / role-change / bulk-import csv
