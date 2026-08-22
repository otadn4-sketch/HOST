#!/bin/sh
# Refresh the live_frontend volume when this image is newer than the files on disk.
set -eu
IMAGE=/opt/eytan/frontend-image
DEST=/usr/share/nginx/html

img=$(cat "$IMAGE/VERSION" 2>/dev/null | tr -d ' \n' || true)
cur=$(cat "$DEST/VERSION" 2>/dev/null | tr -d ' \n' || true)
needs=0
if [ ! -f "$DEST/index.html" ]; then
  needs=1
fi
if [ "${EYTAN_FORCE_IMAGE_SYNC:-}" = "1" ]; then
  needs=1
fi
if [ -n "$img" ]; then
  newest=$(printf '%s\n%s\n' "$cur" "$img" | sort -V | tail -n 1)
  if [ "$newest" = "$img" ] && [ "$img" != "$cur" ]; then
    needs=1
  fi
fi
if [ "$needs" = "1" ] && [ -d "$IMAGE" ]; then
  cp -a "$IMAGE"/. "$DEST"/
  chmod -R a+rX "$DEST" || true
  echo "eytan-frontend-sync: copied image $img over live volume $cur" >&2
fi
