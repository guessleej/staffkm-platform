#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  make-release.sh — 產生「乾淨的銷售交付包」
#
#  規則（CLAUDE.md 已記）：
#  - 來源 = git archive HEAD（只含已提交檔、自動排除 .git / .gitignore / 未追蹤雜物）
#  - 剝除：dev/內部/CI/測試/內部文件/秘密/備份 —— 交付包不該有這些
#  - 保留：客戶部署要的核心（services / packages / apps/web 原始碼 / infra /
#          docs/deploy + user-guide / tools 維運腳本 / 部署範本）
#  - 產出位置：預設 TUT/staffKM/release/（可用 RELEASE_DIR 覆寫）
#
#  用法：
#    ./tools/scripts/make-release.sh                 # → ../../release
#    RELEASE_DIR=/path/to/out ./tools/scripts/make-release.sh
#
#  ⚠ 交付前務必人工複查：無 .env / 無真 key / 預設密碼提醒（見 docs/deploy）。
# ════════════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"   # repo 根 = .../staffKM/code/staffKM-Service
cd "$ROOT"

# 預設產到 TUT/staffKM/release（repo 根往上兩層 = staffKM）
DEST="${RELEASE_DIR:-$(cd "$ROOT/../.." && pwd)/release}"
VER="$(git describe --tags --abbrev=0 2>/dev/null || echo dev)"
COMMIT="$(git rev-parse --short HEAD)"

echo "▶ 產生銷售交付包"
echo "  來源 repo : $ROOT"
echo "  版本      : $VER ($COMMIT)"
echo "  產出位置  : $DEST"

# 1) 乾淨匯出已提交樹（git archive 自動不含 .git / .gitignore / 未追蹤）
rm -rf "$DEST"
mkdir -p "$DEST"
git archive HEAD | tar -x -C "$DEST"

# 2) 剝除 dev / 內部 / 測試 / CI / 內部文件
rm -rf \
  "$DEST/.github" \
  "$DEST/CLAUDE.md" \
  "$DEST/docs/dev" \
  "$DEST/tests" \
  "$DEST/tools/eval" \
  "$DEST/tools/perf" \
  "$DEST/.trivyignore" 2>/dev/null || true
# 各 service / package 的 tests/
find "$DEST/services" "$DEST/packages" -type d -name tests -prune -exec rm -rf {} + 2>/dev/null || true
# integration 測試樹
rm -rf "$DEST/tests" 2>/dev/null || true

# 3) 安全網：確保沒有任何秘密 / 備份 / 建置產物溜進來
find "$DEST" \( \
     -name '.env' -o -name '.env.local' -o -name '.env.production' \
  -o -name '*.bak' -o -name '*.bak-*' -o -name '*.pem' -o -name '*.key' \
  -o -name 'node_modules' -o -name '.venv' -o -name '__pycache__' -o -name 'dist' \
  \) -prune -exec rm -rf {} + 2>/dev/null || true

# 4) 交付包頂層 README（指向部署文件）
cat > "$DEST/README.md" <<EOF
# staffKM — 企業 AI 知識管理平台（交付版 $VER）

> 此為乾淨交付包（由 make-release.sh 產生，commit $COMMIT）。不含開發/測試/CI/內部文件。

## 快速部署
1. 複製 \`.env.production.example\` → \`.env.production\`，填入所有必填值。
   - **務必設 \`STAFFKM_SECRETS_KEY\`**（\`openssl rand -base64 32\`）→ 否則 API key 以明文存。
   - 設強密碼：\`DB_PASSWORD\` / \`REDIS_PASSWORD\` / \`SECRET_KEY\`。
2. \`chmod 600 .env.production\`
3. \`./tools/scripts/safe-redeploy.sh --prod --all\`
4. 驗證：\`curl https://<your-domain>/api/v1/health\`
5. **首次登入後立即更改預設管理員密碼**（見 docs/deploy/production-deploy.md）。

## 文件
- 部署：\`docs/deploy/\`（production-deploy / backup-restore / dr-drill / multi-region）
- 使用者：\`docs/user-guide/\`
- 備份/DR：\`tools/backup/\`（含 dr-drill.sh / replication-failover-drill.sh）

## 預設模型（地端 Ollama）
- 嵌入：snowflake-arctic-embed2（Apache-2.0、多語含繁中、1024 維）
- 系統 LLM：gemma4:e4b
首次啟動 embedder-init 會自動 pull（~11 GB，需網路）。
EOF

# 5) 大小 + 清單摘要
echo "✅ 交付包完成"
echo "  大小: $(du -sh "$DEST" | cut -f1)"
echo "  頂層: $(ls "$DEST" | tr '\n' ' ')"
echo ""
echo "⚠ 交付前人工複查：grep -rIl 'sk-\\|fernet:\\|PASSWORD=' \"$DEST\" 應無真 secret"
