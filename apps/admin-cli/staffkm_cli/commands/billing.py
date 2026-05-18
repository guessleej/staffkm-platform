"""billing — monthly report (table or CSV)."""
from __future__ import annotations

import csv
import sys

import click
from rich.console import Console
from rich.table import Table

from ..api import client

console = Console()


@click.group("billing")
def billing_group() -> None:
    """Billing reports."""


@billing_group.command("report")
@click.option("--month", required=True, help="YYYY-MM")
@click.option("--csv", "as_csv", is_flag=True, help="emit CSV to stdout")
def report(month: str, as_csv: bool) -> None:
    with client() as c:
        r = c.get("/api/v1/admin/billing/report", params={"month": month})
        r.raise_for_status()
        items = (r.json() or {}).get("data", []) or []

    cols = ["workspace_id", "workspace_name", "tokens", "cost_usd", "requests"]
    if as_csv:
        w = csv.writer(sys.stdout)
        w.writerow(cols)
        for row in items:
            w.writerow([row.get(k, "") for k in cols])
        return

    t = Table(title=f"Billing report — {month}")
    for col in cols:
        t.add_column(col)
    for row in items:
        t.add_row(*(str(row.get(k, "")) for k in cols))
    console.print(t)


# TODO (v4.5): per-user breakdown / export PDF / send to email
