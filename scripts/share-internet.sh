#!/usr/bin/env bash
# Temporary public HTTPS URL for the local Docker stack.
# Origin is http://127.0.0.1:80. Stop with Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "This publishes the local Eytan stack on a temporary public HTTPS URL."
echo "Anyone with the URL can reach the login page. Stop with Ctrl+C."
echo

if ! curl -fsS --max-time 5 "http://127.0.0.1/api/health" >/dev/null; then
  echo "http://127.0.0.1/api/health is not reachable."
  echo "Start the stack first: docker compose up -d"
  echo "If this folder is a new zip, also run: ./scripts/apply-source.sh"
  exit 1
fi

BIN="${XDG_CACHE_HOME:-$HOME/.cache}/eytan-tools/cloudflared"
mkdir -p "$(dirname "$BIN")"
if [[ ! -x "$BIN" ]]; then
  echo "Downloading cloudflared (Cloudflare quick tunnel)..."
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64) asset="cloudflared-linux-amd64" ;;
    aarch64|arm64) asset="cloudflared-linux-arm64" ;;
    *) echo "Unsupported architecture: $arch"; exit 1 ;;
  esac
  curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/${asset}" -o "$BIN"
  chmod +x "$BIN"
fi

echo "Starting tunnel. The public URL is printed below (https://....trycloudflare.com)."
echo
exec "$BIN" tunnel --url http://127.0.0.1:80 --no-autoupdate
