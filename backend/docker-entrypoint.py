#!/usr/bin/env python3
"""Start uvicorn after copying a newer image into the live_app volume.

The named volume mounted at /app keeps zip-installed code, but it also hides
image updates from `docker compose build`. Files under /opt/eytan/image stay
inside the image, so a newer VERSION can refresh /app on boot.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

IMAGE = Path("/opt/eytan/image")
DEST = Path(os.environ.get("EYTAN_APP_ROOT", "/app"))


def parse_ver(path: Path) -> tuple[int, int, int]:
    if not path.is_file():
        return (0, 0, 0)
    parts: list[int] = []
    raw = path.read_text(encoding="utf-8").strip()
    for piece in raw.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits or "0"))
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def sync_image() -> None:
    force = os.environ.get("EYTAN_FORCE_IMAGE_SYNC", "").lower() in {"1", "true", "yes"}
    image_v = parse_ver(IMAGE / "VERSION")
    dest_v = parse_ver(DEST / "VERSION")
    has_app = (DEST / "app" / "main.py").is_file()
    if not IMAGE.is_dir():
        return
    if not (force or not has_app or image_v > dest_v):
        return
    DEST.mkdir(parents=True, exist_ok=True)
    for item in IMAGE.iterdir():
        target = DEST / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    print(f"eytan-backend-entry: synced image {image_v} over live volume {dest_v}", file=sys.stderr)


def main() -> None:
    try:
        sync_image()
    except Exception as exc:
        print(f"eytan-backend-entry: sync failed: {exc}", file=sys.stderr)
    os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])


if __name__ == "__main__":
    main()
