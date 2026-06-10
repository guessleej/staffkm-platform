#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  gen-dev-cert.sh — 產生自簽 TLS 憑證（含本機 LAN IP）
#
#  dev / 地端純內網（無公網域名、無法 Let's Encrypt）走 HTTPS 用。
#  產出 dev.crt / dev.key 到本目錄（已被 .gitignore，不進版控）。
#
#  SAN 自動含：localhost / staffkm.local / 127.0.0.1 / 本機所有 LAN IP
#  （自動偵測），另可用 EXTRA_SAN 補（逗號分隔），例：
#    EXTRA_SAN="IP:192.168.11.50,DNS:km.corp" ./gen-dev-cert.sh
#
#  用法：
#    ./infra/nginx/ssl/gen-dev-cert.sh          # 已存在則跳過
#    FORCE=1 ./infra/nginx/ssl/gen-dev-cert.sh  # 強制重產（換 IP 後用）
#
#  瀏覽器會警告自簽（預期）；要免警告把 dev.crt 加進各機器系統信任。
# ════════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")"

if [ -f dev.crt ] && [ -f dev.key ] && [ "${FORCE:-0}" != "1" ]; then
  echo "dev.crt / dev.key 已存在；要重產請 FORCE=1 重跑。"
  exit 0
fi

# 偵測本機所有 IPv4（排除 loopback），組成 SAN 的 IP: 條目
ips="$(hostname -I 2>/dev/null || ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1)"
san="DNS:localhost,DNS:staffkm.local,IP:127.0.0.1"
for ip in $ips; do
  case "$ip" in
    127.*|"") ;;
    *) san="${san},IP:${ip}" ;;
  esac
done
[ -n "${EXTRA_SAN:-}" ] && san="${san},${EXTRA_SAN}"

openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
  -keyout dev.key -out dev.crt \
  -subj "/C=TW/O=staffKM-dev/CN=staffkm.local" \
  -addext "subjectAltName=${san}"

chmod 600 dev.key
echo "✅ 產生 dev.crt / dev.key"
echo "   SAN: ${san}"
