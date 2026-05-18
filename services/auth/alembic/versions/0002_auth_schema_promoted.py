"""auth schema promoted from bootstrap_ddl (v4.0-P1)

把 v3.1 之前在 services/auth/app/main.py `_AUTH_BOOTSTRAP_DDL` 內的
idempotent ALTER/CREATE/UPDATE 全部轉成 alembic revision，內容相同，
保留 IF NOT EXISTS 以兼容已執行過 bootstrap 的舊 deploy。

Revision ID: 0002_auth_schema_promoted
Revises: 0001_baseline
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_auth_schema_promoted"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # v3.0：OIDC SSO 正規欄位（idempotent；既有 bootstrap 已執行過的 deploy no-op）
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oidc_sub VARCHAR(256)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oidc_issuer VARCHAR(256)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_oidc_sub "
        "ON users(oidc_sub) WHERE oidc_sub IS NOT NULL"
    )
    # 遷移：把 v2.x 借用 ldap_dn 存的 oidc:{sub} 搬到 oidc_sub
    op.execute(
        "UPDATE users SET oidc_sub = SUBSTRING(ldap_dn FROM 6) "
        "WHERE ldap_dn LIKE 'oidc:%' AND oidc_sub IS NULL"
    )


def downgrade() -> None:
    # 不 drop — schema 退版會 break 已生產資料
    pass
