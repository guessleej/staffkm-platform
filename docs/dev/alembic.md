# Alembic — Schema 變更唯一管道（v4.0+）

> v4.0 起，`bootstrap_ddl.py` 跟 main.py 內各種 `_*_BOOTSTRAP_DDL` list 全部移除。
> Schema 變更**只**走 alembic revision。

## 核心原則

1. **唯一管道**：任何 schema 變更（CREATE TABLE / ALTER TABLE / 加 index / 加 constraint / 資料回填）只能透過 `alembic revision -m "..."` 建立新 revision，提交到 `services/{service}/alembic/versions/`。
2. **不要在 main.py 加 idempotent DDL**：v3.1 以前的 `ALTER ... ADD COLUMN IF NOT EXISTS` 啟動補丁 pattern 已棄用。新增請寫進 alembic revision。
3. **lifespan 只跑 `run_alembic_upgrade()`**：lifespan 內不該有 `await _run_*_bootstrap_ddl()`。
4. **多 instance 並發安全**：`run_alembic_upgrade` 用 PostgreSQL advisory lock 保證同一 service 多 replica 同時起 pod 時，只會有一個跑 migration，其他等到完成才繼續。
5. **idempotent 保留**：alembic 內部仍可以用 `op.execute("ALTER ... IF NOT EXISTS ...")`，這樣老 deploy（曾經跑過 bootstrap DDL）升 v4.0 時不會炸。

## 新增 revision 範例

```bash
cd services/agent
alembic revision -m "add foo_table"
```

```python
# services/agent/alembic/versions/0015_add_foo_table.py
def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS foo (
            id UUID PRIMARY KEY,
            ...
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_foo_x ON foo(x)")

def downgrade() -> None:
    pass  # 一般不退版；如要寫請小心 prod 資料
```

## 對舊 deploy 升 v4.0 的注意事項

- v3.1 以前的 deploy 跑過 bootstrap DDL，已有對應欄位 → alembic `0002_*_schema_promoted` 內的 `IF NOT EXISTS` 直接 no-op。
- v3.0 以前**沒跑過** bootstrap 的 deploy 不存在（v3.1 是過渡期）。
- 全新 deploy → alembic chain 從 0001 一路跑到 head。

## 各 service alembic chain 現況（v4.0-P1）

| Service | Head | 備註 |
|---|---|---|
| agent | 0014_slow_query_explains | 完整 chain，沒有缺洞 |
| auth | 0002_auth_schema_promoted | 把 OIDC SSO 兩個欄位轉進來 |
| knowledge | 0002_knowledge_schema_promoted | 把 bootstrap_ddl 內 15+ 個 schema 變更轉進來 |
| chat | 0001_baseline | no-op；歷來無 bootstrap DDL |

## 不要做

- ❌ 在 main.py 加 `await conn.execute(text("ALTER TABLE ..."))`
- ❌ 跳過 alembic 直接 `psql` 改 prod schema
- ❌ 編輯歷史 revision（即使是「為了修小 bug」） — 改用新 revision 補
