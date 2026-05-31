#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
#  publish-release.sh — 把乾淨交付包發佈到 private GitHub repo + GitHub Release
# ════════════════════════════════════════════════════════════════════════════
#  流程：make-release（產乾淨包）→ secret 安全閘 → 同步進「乾淨 release repo」
#        → commit/tag/push → 打包 zip → gh release create（附 zip 當下載資產）。
#
#  ⚠ 這是**內部發佈工具**，不會進交付包（make-release 已剝除）。
#  ⚠ private repo 的 Release 資產：客戶需有該 repo **read 權限**才下載得到
#     （加為 read-only collaborator / Team）。詳見 docs/deploy。
#
#  用法：
#    RELEASE_REPO=git@github.com:你的組織/staffkm-release.git \
#      tools/scripts/publish-release.sh v5.12.62
#
#  前置：已裝並登入 gh（gh auth login）、對 RELEASE_REPO 有 push 權。
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

VERSION="${1:?用法: RELEASE_REPO=... publish-release.sh vX.Y.Z}"
RELEASE_REPO="${RELEASE_REPO:?請設 RELEASE_REPO=git@github.com:org/staffkm-release.git}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_BASE="$(cd "$ROOT/../.." && pwd)"          # TUT/staffKM
STAGE="$OUT_BASE/release"                       # make-release 預設輸出
WORK="$OUT_BASE/release-repo"                    # 持久 git 工作副本（保留歷史）
ZIP="$OUT_BASE/staffkm-$VERSION.zip"
REPO_SLUG="$(echo "$RELEASE_REPO" | sed -E 's#.*github.com[:/]+([^/]+/[^/.]+)(\.git)?$#\1#')"

echo "▶ 1/5 產乾淨交付包…"
"$ROOT/tools/scripts/make-release.sh"

echo "▶ 2/5 secret 安全閘…"
# 只攔「高信度真 secret 特徵」，排除：① 變數參照（=$VAR / =${VAR}）② 出廠預設 dev 密碼
# （staffkm_secret/redis/minio/grafana）③ docstring/註解在說明格式的字面字串（fernet: 前綴、
# sk-xxxx 範例）④ 文件遮罩（***）⑤ *.example。避免 false positive 卡死每次發佈。
# 真特徵：OpenAI key（sk-+20碼）、fernet 密文（fernet:gAAAA+base64）、賦值給 16+ 碼高熵 token。
SECRET_HITS="$(grep -rInE \
  'sk-[A-Za-z0-9_-]{20,}|fernet:gAAAA[A-Za-z0-9_=-]{16,}|(PASSWORD|SECRET_KEY|API_KEY|TOKEN)=[A-Za-z0-9+/]{16,}' \
  "$STAGE" 2>/dev/null \
  | grep -vE '/\.git/' \
  | grep -vE '\.example' \
  | grep -vE '=["'\'']?\$\{?[A-Za-z_]' \
  | grep -viE '(staffkm_secret|staffkm_redis|staffkm_minio|staffkm_grafana|change[-_]?me|your[-_]|example|xxxx|placeholder|<[^>]+>|\*\*\*)' \
  || true)"
if [ -n "$SECRET_HITS" ]; then
  echo "✗ 偵測到疑似真 secret，**中止發佈**。請檢查下列位置（檔:行）："
  echo "$SECRET_HITS"
  exit 1
fi
echo "  ✓ 無真 secret"

echo "▶ 3/5 同步進乾淨 release repo（保留 .git 歷史）…"
if [ ! -d "$WORK/.git" ]; then
  git clone "$RELEASE_REPO" "$WORK" 2>/dev/null || {
    mkdir -p "$WORK"; ( cd "$WORK" && git init -q && git remote add origin "$RELEASE_REPO" )
  }
fi
rsync -a --delete --exclude='.git' "$STAGE/" "$WORK/"   # 覆蓋內容、刪掉交付包已移除的舊檔
( cd "$WORK"
  git add -A
  git commit -q -m "staffKM $VERSION release" || echo "  （內容無變更，沿用前次 commit）"
  git tag -f "$VERSION"
  # 推「當前 HEAD」成遠端 main，不依賴本地分支名（空 repo clone 後本地可能是 master /
  # claude-* / 隨機器 init.defaultBranch）→ 避免 "src refspec main does not match any"。
  git push -u origin HEAD:main
  git push -f origin "refs/tags/$VERSION"
)

echo "▶ 4/5 打包 zip…"
rm -f "$ZIP"
( cd "$STAGE" && zip -rq "$ZIP" . )
echo "  ✓ ${ZIP}（$(du -sh "$ZIP" | cut -f1)）"

echo "▶ 5/5 發 GitHub Release…"
gh release create "$VERSION" "$ZIP" --repo "$REPO_SLUG" \
   --title "staffKM $VERSION" \
   --notes "安裝見交付包內 docs/deploy/production-deploy.md。下載此 zip 解壓即可部署。" \
   || gh release upload "$VERSION" "$ZIP" --repo "$REPO_SLUG" --clobber

echo ""
echo "✅ 發佈完成：$VERSION → $REPO_SLUG"
echo "   客戶（已加 read 權）到 Releases 下載：staffkm-$VERSION.zip"
