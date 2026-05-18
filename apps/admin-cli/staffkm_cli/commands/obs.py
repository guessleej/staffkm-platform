"""observability — slow-queries / heartbeats / webhook-outbox."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..api import client

console = Console()


@click.group("observability")
def obs_group() -> None:
    """Operational observability views."""


@obs_group.command("slow-queries")
@click.option("--limit", default=20, type=int)
def slow_queries(limit: int) -> None:
    with client() as c:
        r = c.get("/api/v1/admin/observability/slow-queries", params={"limit": limit})
        r.raise_for_status()
        items = (r.json() or {}).get("data", []) or []
    t = Table(title=f"Slow queries (top {limit})")
    for col in ("ts", "duration_ms", "endpoint", "query_preview"):
        t.add_column(col)
    for q in items:
        t.add_row(
            str(q.get("ts", ""))[:19],
            str(q.get("duration_ms", "")),
            q.get("endpoint", ""),
            (q.get("query") or "")[:60],
        )
    console.print(t)


@obs_group.command("heartbeats")
def heartbeats() -> None:
    """Worker / service heartbeats."""
    with client() as c:
        r = c.get("/api/v1/admin/observability/heartbeats")
        r.raise_for_status()
        items = (r.json() or {}).get("data", []) or []
    t = Table(title=f"Heartbeats ({len(items)})")
    for col in ("service", "instance", "last_seen", "status"):
        t.add_column(col)
    for h in items:
        t.add_row(h.get("service", ""), h.get("instance", ""), str(h.get("last_seen", ""))[:19], h.get("status", ""))
    console.print(t)


@obs_group.command("webhook-outbox")
@click.option("--state", default="failed", type=click.Choice(["pending", "delivered", "failed"]))
def webhook_outbox(state: str) -> None:
    with client() as c:
        r = c.get("/api/v1/admin/observability/webhook-outbox", params={"state": state})
        r.raise_for_status()
        items = (r.json() or {}).get("data", []) or []
    t = Table(title=f"Webhook outbox — {state} ({len(items)})")
    for col in ("id", "url", "attempts", "last_error"):
        t.add_column(col)
    for w in items:
        t.add_row(
            str(w.get("id", ""))[:8],
            w.get("url", "")[:40],
            str(w.get("attempts", 0)),
            (w.get("last_error") or "")[:40],
        )
    console.print(t)


# TODO (v4.5): trace tail / metric snapshot / alert ack
