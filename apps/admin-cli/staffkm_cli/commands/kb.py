"""kb — list / create / upload / search."""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ..api import client

console = Console()


@click.group("kb")
def kb_group() -> None:
    """Knowledge base management."""


@kb_group.command("list")
def kb_list() -> None:
    with client() as c:
        r = c.get("/api/v1/knowledge-bases")
        r.raise_for_status()
        items = (r.json() or {}).get("data", []) or []
    t = Table(title=f"Knowledge Bases ({len(items)})")
    for col in ("id", "name", "doc_count"):
        t.add_column(col)
    for kb in items:
        t.add_row(str(kb.get("id", ""))[:8], kb.get("name", ""), str(kb.get("doc_count", "-")))
    console.print(t)


@kb_group.command("create")
@click.argument("name")
def create(name: str) -> None:
    with client() as c:
        r = c.post("/api/v1/knowledge-bases", json={"name": name})
        r.raise_for_status()
        data = (r.json() or {}).get("data") or {}
    click.echo(f"OK  created kb id={data.get('id')} name={data.get('name')}")


@kb_group.command("upload")
@click.argument("kb_id")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
def upload(kb_id: str, file_path: str) -> None:
    """Upload a document to KB."""
    p = Path(file_path)
    with client() as c, p.open("rb") as fh:
        files = {"file": (p.name, fh, "application/octet-stream")}
        r = c.post(f"/api/v1/knowledge-bases/{kb_id}/documents", files=files)
        r.raise_for_status()
        data = (r.json() or {}).get("data") or {}
    click.echo(f"OK  uploaded {p.name} -> doc id={data.get('id')}")


@kb_group.command("search")
@click.argument("kb_id")
@click.argument("query")
@click.option("--top-k", default=5, type=int)
def search(kb_id: str, query: str, top_k: int) -> None:
    with client() as c:
        r = c.post(
            f"/api/v1/knowledge-bases/{kb_id}/search",
            json={"query": query, "top_k": top_k},
        )
        r.raise_for_status()
        hits = (r.json() or {}).get("data", []) or []
    for i, h in enumerate(hits, 1):
        console.print(f"[bold]#{i}[/bold]  score={h.get('score', 0):.3f}")
        console.print(f"  {h.get('content', '')[:200]}")


# TODO (v4.5): delete-doc / reindex / hit-test / web-sync trigger
