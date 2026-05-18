# Workflow Marketplace（v4.10 Theme J）

> 跨 org 公開 template gallery — 任何人不需登入都能瀏覽、登入後可 install。

## v2.5-C vs v4.10 J

| 維度 | v2.5-C | v4.10 J |
|---|---|---|
| API 路徑 | `/api/v1/workspace/{ws}/app-templates/marketplace` | `/api/v1/public/marketplace` |
| 認證 | 需 JWT + workspace 成員 | READ 不需 JWT；rate 才需 JWT |
| 範圍 | 同 platform 內跨 workspace | 跨 org 公開 |
| 篩選 | 無 | category / tag / search / sort |
| 評分 | 無 | 1–5 ★ + 留言（unique by user） |
| Publisher metadata | 無 | publisher_name / url / cover / verified |
| install endpoint | v2.5 `marketplace/{id}/install` | **沿用 v2.5**（install 一律 workspace-scoped） |

兩套並存 — v2.5 是「給 workspace 成員看的 marketplace」，v4.10 是「給全世界看的 public gallery」。

## Schema 變動（alembic 0018）

`workspace_app_templates` add columns：

| 欄位 | 型別 | 預設 | 用途 |
|---|---|---|---|
| `publisher_name`   | VARCHAR(64) | NULL    | 顯示出版者名 |
| `publisher_url`    | TEXT        | NULL    | 出版者連結 |
| `cover_image_url`  | TEXT        | NULL    | 卡片封面 |
| `category`         | VARCHAR(32) | NULL    | hr / sales / engineering... |
| `tags`             | JSONB       | `[]`    | 多 tag 篩選 |
| `license`          | VARCHAR(32) | `MIT`   | |
| `verified`         | BOOLEAN     | FALSE   | staffKM team 手動加 |
| `rating_avg`       | NUMERIC(3,2)| NULL    | trigger free，rate API 重算 |
| `rating_count`     | INT         | 0       | |

新表 `template_ratings`：PK `(template_id, user_id)`；同 user 對同 template 多次 rate 走 UPSERT。

兩個索引：
- `idx_template_public_install` partial idx on `(is_public, install_count DESC) WHERE is_public`
- `idx_template_category`        partial idx on `(category, install_count DESC) WHERE is_public`

## 發布流程

任何 workspace owner / writer 在 `/app-templates` 對自己模板按「設為 public」即可（v2.5 已有 `is_public` 欄）。

要補 marketplace metadata（publisher / category / tags / cover）目前需要 SQL：

```sql
UPDATE workspace_app_templates SET
  publisher_name = 'staffKM team',
  category       = 'hr',
  tags           = '["hr","qa","knowledge"]'::jsonb,
  cover_image_url = 'https://...',
  verified       = TRUE
WHERE id = '...';
```

未來可在 `/app-templates` UI 加 publisher form（v4.x backlog）。

## Rating 機制

- 1–5 整數；同 user 對同 template 二次 rate 會 UPSERT（覆寫前值）
- `rating_avg / rating_count` 在 rate API 內**同 transaction 重算**（簡單一致；模板量級 < 數千時夠用）
- 大規模情境改 trigger 或 materialised view

## Verified 標誌

`verified=TRUE` 由 staffKM 官方人工 review 後加（手動 SQL）。
UI 顯示 ✓ 徽章，讓使用者識別「官方品質」與「社群投稿」。

## API 範例

```bash
# 列熱門 hr 模板
curl 'http://localhost/api/v1/public/marketplace?category=hr&sort=popular&page=1&page_size=20'

# 取詳情
curl 'http://localhost/api/v1/public/marketplace/<uuid>'

# 取分類列表
curl 'http://localhost/api/v1/public/marketplace/categories'

# 評分（需 JWT）
curl -X POST 'http://localhost/api/v1/public/marketplace/<uuid>/rate' \
     -H "Authorization: Bearer $JWT" \
     -H 'Content-Type: application/json' \
     -d '{"rating": 5, "comment": "很好用"}'
```

## 三層 routing（CLAUDE.md §7）

1. agent `main.py`：`include_router(marketplace.router, prefix="/api/v1/public/marketplace")`
2. legacy_bridge：不需動（public path 不走 workspace 翻譯）
3. gateway `main.py` + `_make_public_marketplace_router()`：proxy 到 agent

`PUBLIC_PREFIXES` 已含 `/api/v1/public/` — 不需動 auth middleware。

## Frontend

- `/marketplace` → `MarketplaceHomeView.vue`（card grid + filter）
- `/marketplace/:id` → `MarketplaceDetailView.vue`（detail + rate + install CTA）
- 兩條路由都 `meta.public = true`，跳過 auth guard
- 未登入點「Install」→ `/login?next=/marketplace/{id}` redirect

## 未做（留 backlog）

- Template versioning（v4.x）
- Tarball download（template 已在 DB schema_json，不需）
- Fork / star（v5.x）
- 站內 publisher onboarding UI（目前手動 SQL）
