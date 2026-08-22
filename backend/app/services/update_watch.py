from __future__ import annotations

import os
import threading
import time
from pathlib import Path


def start_update_stamp_watch(path: Path | None = None) -> None:
    """Exit the process when update-agent writes a new stamp so Docker restarts uvicorn."""
    if os.environ.get("EYTAN_ENV", "").lower() == "development":
        return
    stamp = path or Path("/app/.update-stamp")

    def loop() -> None:
        last = stamp.read_text(encoding="utf-8") if stamp.exists() else ""
        while True:
            time.sleep(4)
            try:
                now = stamp.read_text(encoding="utf-8") if stamp.exists() else last
            except OSError:
                continue
            if now and now != last:
                os._exit(0)

    threading.Thread(target=loop, name="update-stamp-watch", daemon=True).start()
