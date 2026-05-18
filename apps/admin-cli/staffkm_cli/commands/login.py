"""login / logout — store JWT to ~/.staffkm/credentials.json."""
from __future__ import annotations

import click
import httpx

from ..config import clear_credentials, save_credentials


@click.command("login")
@click.option("--base", required=True, help="staffKM gateway URL, e.g. http://localhost")
@click.option("--email", required=True)
@click.option("--password", required=True, prompt=True, hide_input=True)
def login_cmd(base: str, email: str, password: str) -> None:
    """Login to staffKM and save token to ~/.staffkm/credentials.json."""
    base = base.rstrip("/")
    try:
        r = httpx.post(
            f"{base}/api/v1/auth/login",
            json={"username": email, "password": password},
            timeout=30.0,
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise click.ClickException(f"login HTTP error: {e}")
    data = r.json()
    # 兼容 {access_token} 或 {data: {access_token}}
    token = data.get("access_token") or (data.get("data") or {}).get("access_token")
    if not token:
        raise click.ClickException(f"no access_token in response: {data}")
    save_credentials(base, token)
    click.echo(f"OK  logged in as {email}  ({base})")


@click.command("logout")
def logout_cmd() -> None:
    """Clear ~/.staffkm/credentials.json."""
    clear_credentials()
    click.echo("OK  logged out")
