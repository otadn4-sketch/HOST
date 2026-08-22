#!/usr/bin/env python3
"""Local update-agent: optional helper. Primary install is done by the backend.

This process does not execute install.sh, docker-compose.yml, or any script from the ZIP.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.services.release_bundle import current_version, verify_and_extract
from app.services.updater import apply_extracted_release, maybe_upgrade_alembic

TOKEN = os.environ.get("UPDATE_AGENT_TOKEN", "")
PUBLIC_KEY = os.environ.get("UPDATE_PUBLIC_KEY", "")
STAGING = Path(os.environ.get("STAGING_PATH", "/var/lib/eytan/staging"))
RELEASES = Path(os.environ.get("RELEASES_PATH", "/var/lib/eytan/releases"))
CURRENT = Path(os.environ.get("CURRENT_RELEASE_PATH", "/var/lib/eytan/releases/current"))
OVERLAY_APP = Path(os.environ.get("OVERLAY_APP_PATH", "/overlay/app"))
OVERLAY_FRONTEND = Path(os.environ.get("OVERLAY_FRONTEND_PATH", "/overlay/frontend"))

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class InstallIn(BaseModel):
    update_id: str
    staging_name: str
    version: str
    migration_id: str = ""
    initiated_by: str = ""
    touch_stamp: bool = False


def _auth(token: str | None) -> None:
    expected = TOKEN.strip()
    provided = (token or "").strip()
    if expected and provided != expected:
        raise HTTPException(status_code=403, detail="forbidden")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/install")
def install(payload: InstallIn, x_update_token: str | None = Header(default=None)):
    _auth(x_update_token)
    bundle = STAGING / payload.staging_name
    if not bundle.is_file():
        raise HTTPException(status_code=400, detail="staging bundle missing")

    work = STAGING / f"install-{payload.update_id}"
    if work.exists():
        shutil.rmtree(work)
    result = verify_and_extract(bundle, PUBLIC_KEY, work, allow_unsigned=True)
    if not result.ok:
        return {"ok": False, "error": "; ".join(result.errors), "rolled_back": False}

    previous = current_version(CURRENT if CURRENT.exists() else Path("."))
    dest = RELEASES / payload.version
    try:
        dest.mkdir(parents=True, exist_ok=True)
        for item in ("frontend", "backend", "VERSION", "CHANGELOG.md"):
            src = work / item
            if src.exists():
                target = dest / item
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                if src.is_dir():
                    shutil.copytree(src, target)
                else:
                    shutil.copy2(src, target)

        os.environ.setdefault("EYTAN_APP_ROOT", str(OVERLAY_APP if OVERLAY_APP.exists() else "/app"))
        os.environ.setdefault("OVERLAY_FRONTEND_PATH", str(OVERLAY_FRONTEND))
        notes = apply_extracted_release(work)
        if payload.migration_id:
            notes.append(maybe_upgrade_alembic())
        tmp_link = RELEASES / f"current-{payload.version}.tmp"
        if tmp_link.exists() or tmp_link.is_symlink():
            tmp_link.unlink()
        tmp_link.symlink_to(dest)
        tmp_link.replace(CURRENT)
        if payload.touch_stamp:
            stamp = Path(os.environ["EYTAN_APP_ROOT"]) / ".update-stamp"
            stamp.write_text(str(time.time()), encoding="utf-8")
        return {"ok": True, "version": payload.version, "previous": previous, "notes": notes}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "rolled_back": False}
    finally:
        shutil.rmtree(work, ignore_errors=True)
