"""users.allowed_login_methods (v2.7 X-Pack)

Per-user login method whitelist：NULL = 全部允許；非 NULL 則 /auth/login
（password）+ /auth/oidc/callback + /auth/oauth/{google,github}/callback
在發 token 前必須驗證當前 method 在白名單中。

Revision ID: 0003_user_allowed_login_methods
Revises: 0002_auth_schema_promoted
Create Date: 2026-05-19
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003_user_allowed_login_methods"
down_revision: Union[str, None] = "0002_auth_schema_promoted"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users "
        "ADD COLUMN IF NOT EXISTS allowed_login_methods VARCHAR[] "
        "DEFAULT NULL"
    )


def downgrade() -> None:
    # 不 drop — schema 退版會 break 已生產資料
    pass
