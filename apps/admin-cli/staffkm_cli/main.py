"""staffKM CLI — admin / ops 工具。

設定（任一）：
  - 環境變數 STAFFKM_BASE_URL / STAFFKM_API_KEY / STAFFKM_WORKSPACE_ID
  - 旗標 --base-url / --api-key / --workspace

範例：
  staffkm ping
  staffkm apps list
  staffkm chat --app-id ... "今天天氣？"
  staffkm usage summary
  staffkm quota set --tokens 1000000 --cost 50
"""
from __future__ import annotations

import json
import os
import sys

import click
from rich.console import Console
from rich.table import Table

from staffkm_sdk import AuthError, QuotaExceeded, StaffKMClient, StaffKMError

console = Console()


def _make_client(ctx: click.Context) -> StaffKMClient:
    base = ctx.obj["base_url"] or os.environ.get("STAFFKM_BASE_URL")
    key  = ctx.obj["api_key"]  or os.environ.get("STAFFKM_API_KEY")
    ws   = ctx.obj["workspace"] or os.environ.get("STAFFKM_WORKSPACE_ID")
    if not all([base, key, ws]):
        raise click.UsageError(
            "需設定 base-url / api-key / workspace（旗標或環境變數）"
        )
    return StaffKMClient(base_url=base, api_key=key, workspace_id=ws)


@click.group()
@click.option("--base-url", default=None, help="API base URL")
@click.option("--api-key",  default=None, help="API key（Bearer token）")
@click.option("--workspace", default=None, help="workspace id")
@click.pass_context
def cli(ctx: click.Context, base_url, api_key, workspace):
    """staffKM admin CLI."""
    ctx.ensure_object(dict)
    ctx.obj["base_url"]  = base_url
    ctx.obj["api_key"]   = api_key
    ctx.obj["workspace"] = workspace


# ── 基本 ─────────────────────────────────────────────────────────────
@cli.command()
@click.pass_context
def ping(ctx):
    """檢查連線（呼叫 /usage/summary，能拿就 OK）"""
    with _make_client(ctx) as c:
        try:
            s = c.usage.summary()
            console.print(f"[green]✓ OK[/green]  month={s.get('month')}  tokens={s.get('usage', {}).get('tokens')}")
        except (AuthError, QuotaExceeded, StaffKMError) as e:
            console.print(f"[red]✗ {type(e).__name__}: {e}[/red]")
            sys.exit(1)


# ── apps ──────────────────────────────────────────────────────────────
@cli.group()
def apps():
    """Application 管理"""


@apps.command("list")
@click.pass_context
def apps_list(ctx):
    with _make_client(ctx) as c:
        items = c.apps.list()
        t = Table(title=f"Applications ({len(items)})")
        for col in ("id", "name", "type", "status"):
            t.add_column(col)
        for a in items:
            t.add_row(str(a.get("id", "")), a.get("name", ""), a.get("type", ""), a.get("status", ""))
        console.print(t)


# ── chat ──────────────────────────────────────────────────────────────
@cli.command()
@click.option("--app-id", required=True)
@click.argument("message", nargs=-1, required=True)
@click.option("--stream/--no-stream", default=True)
@click.pass_context
def chat(ctx, app_id, message, stream):
    """與 application 對話"""
    msg = " ".join(message)
    with _make_client(ctx) as c:
        if stream:
            for chunk in c.chat_stream(app_id=app_id, message=msg):
                console.print(chunk, end="", soft_wrap=True)
            console.print()
        else:
            res = c.chat(app_id=app_id, message=msg)
            console.print(res.content)
            if res.citations:
                console.print(f"\n[dim]{len(res.citations)} citations[/dim]")


# ── usage ─────────────────────────────────────────────────────────────
@cli.group()
def usage():
    """Token / Quota 管理"""


@usage.command("summary")
@click.pass_context
def usage_summary(ctx):
    with _make_client(ctx) as c:
        s = c.usage.summary()
        console.print_json(json.dumps(s))


@usage.command("logs")
@click.option("--page", default=1)
@click.option("--page-size", default=20)
@click.pass_context
def usage_logs(ctx, page, page_size):
    with _make_client(ctx) as c:
        data = c.usage.logs(page=page, page_size=page_size)
        items = data.get("items") or []
        t = Table(title=f"Usage logs (page {page})")
        for col in ("created_at", "provider_type", "model", "total_tokens", "cost_usd", "status"):
            t.add_column(col)
        for r in items:
            t.add_row(
                str(r.get("created_at", "")),
                str(r.get("provider_type", "")),
                str(r.get("model", "")),
                str(r.get("total_tokens", 0)),
                str(r.get("cost_usd", 0)),
                str(r.get("status", "")),
            )
        console.print(t)


# ── quota ─────────────────────────────────────────────────────────────
@cli.group()
def quota():
    """設定 workspace quota"""


@quota.command("get")
@click.pass_context
def quota_get(ctx):
    with _make_client(ctx) as c:
        console.print_json(json.dumps(c.usage.quota()))


@quota.command("set")
@click.option("--tokens", type=int, default=None, help="monthly_token_cap，留空表示不變")
@click.option("--cost",   type=float, default=None, help="monthly_cost_cap_usd")
@click.pass_context
def quota_set(ctx, tokens, cost):
    with _make_client(ctx) as c:
        result = c.usage.set_quota(monthly_token_cap=tokens, monthly_cost_cap_usd=cost)
        console.print_json(json.dumps(result))


if __name__ == "__main__":
    cli()
