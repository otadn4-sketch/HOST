#!/usr/bin/env bash
set -euo pipefail
# Local/compose health: try public HTTPS first, then backend loopback.
if curl -fsS --max-time 5 "https://${PUBLIC_HOST:-localhost}/api/health" >/dev/null 2>&1; then
  echo "health ok (https ${PUBLIC_HOST:-localhost})"
  exit 0
fi
if curl -fsS --max-time 5 "http://127.0.0.1:8000/api/health" >/dev/null 2>&1; then
  echo "health ok (backend loopback)"
  exit 0
fi
echo "health check failed" >&2
exit 1
