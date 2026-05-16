# 備份與災難復原

> 詳見 [Backup/DR Runbook](https://github.com/guessleej/staffkm-platform/blob/main/docs/ops/backup-dr-runbook.md)

## 摘要

| 目標     | 值                          |
| -------- | --------------------------- |
| RPO      | ≤ 15 min（managed Postgres） |
| RTO      | ≤ 1 hour                    |
| 演練週期 | 每月一次                    |

## 三個必做

1. **Postgres**：用 managed 服務 + 啟用 PITR
2. **STAFFKM_SECRETS_KEY**：脫離 git，存 KMS / Vault；定期 rotate
3. **每月演練**：clone snapshot → 跑 wait-healthy + e2e → 寫紀錄

## 升級 / Rollback

```bash
# 升級
helm upgrade staffkm ./infra/helm/staffkm --set image.tag=2.0.1

# Rollback（前一版）
helm rollback staffkm 0
```
