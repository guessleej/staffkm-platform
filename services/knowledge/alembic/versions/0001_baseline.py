"""baseline — schema 由 bootstrap_ddl.py 既有狀態接管，未來改動走 alembic revisions

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-18
"""
from typing import Sequence, Union

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
