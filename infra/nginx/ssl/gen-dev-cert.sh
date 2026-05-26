#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  gen-dev-cert.sh — 產生 dev 用自簽 TLS 憑證（localhost）
#
#  dev nginx 走 HTTPS 用（prod 由 Caddy 自動 Let's Encrypt，不用這支）。
#  產出 dev.crt / dev.key 到本目錄（已被 .gitignore，不進版控）。
#
#  用法：
#    ./infra/nginx/ssl/gen-dev-cert.sh
#  瀏覽器會警告自簽（dev 預期）；要免警告可把 dev.crt 加進系統信任。
# ════════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")"

if [ -f dev.crt ] && [ -f dev.key ]; then
  echo "dev.crt / dev.key 已存在；要重產請先刪除。"
  exit 0
fi

openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
  -keyout dev.key -out dev.crt \
  -subj "/C=TW/O=staffKM-dev/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:staffkm.local,IP:127.0.0.1"

chmod 600 dev.key
echo "✅ 產生 dev.crt / dev.key（CN=localhost, SAN: localhost/staffkm.local/127.0.0.1）"
