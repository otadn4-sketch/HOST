#!/usr/bin/env bash
set -euo pipefail
curl -fsS "https://${PUBLIC_HOST:-localhost}/api/health" >/dev/null
echo "health ok"
