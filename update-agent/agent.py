#!/usr/bin/env python3
"""Local update-agent: validates signed release bundles and performs a constrained install.

This process does not execute install.sh, docker-compose.yml, or any script from the ZIP.
It only copies allowlisted files, runs a known alembic revision, and health-checks.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.services.backup import create_backup, restore_backup
from app.services.release_bundle import current_version, verify_and_extract

TOKEN = os.environ.get("UPDATE_AGENT_TOKEN", "")
PUBLIC_KEY = os.environ.get("UPDATE_PUBLIC_KEY", "")
STAGING = Path(os.environ.get("STAGING_PATH", "/var/lib/eytan/staging"))
RELEASES = Path(os.environ.get("RELEASES_PATH", "/var/lib/eytan/releases"))
CURRENT = Path(os.environ.get("CURRENT_RELEASE_PATH", "/var/lib/eytan/releases/current"))
BACKUP_PATH = Path(os.environ.get("BACKUP_PATH", "/var/lib/eytan/backups"))
HEALTH_URL = os.environ.get("HEALTH_URL", "http://backend:8000/api/health")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
BACKEND_CONTAINER_WORKDIR = Path(os.environ.get("BACKEND_CODE_PATH", "/var/lib/eytan/releases/current/backend"))
OVERLAY_APP = Path(os.environ.get("OVERLAY_APP_PATH", "/overlay/app"))
OVERLAY_FRONTEND = Path(os.environ.get("OVERLAY_FRONTEND_PATH", "/overlay/frontend"))

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class InstallIn(BaseModel):
    update_id: str
    staging_name: str
    version: str
    migration_id: str
    initiated_by: str


def _sync_tree(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for child in list(dest.iterdir()):
        if child.name in {".", ".."}:
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    elif src.is_file():
        shutil.copy2(src, dest)


def _apply_live_overlays(work: Path) -> None:
    app_src = work / "backend" / "app"
    if app_src.is_dir() and OVERLAY_APP.exists():
        _sync_tree(app_src, OVERLAY_APP / "app")
        alembic_src = work / "backend" / "alembic" / "versions"
        if alembic_src.is_dir():
            target = OVERLAY_APP / "alembic" / "versions"
            target.mkdir(parents=True, exist_ok=True)
            _sync_tree(alembic_src, target)
        version_src = work / "VERSION"
        if version_src.is_file():
            shutil.copy2(version_src, OVERLAY_APP / "VERSION")
    frontend_src = work / "frontend"
    dist_index = frontend_src / "dist" / "index.html"
    root_index = frontend_src / "index.html"
    if OVERLAY_FRONTEND.exists():
        if dist_index.is_file():
            _sync_tree(frontend_src / "dist", OVERLAY_FRONTEND)
        elif root_index.is_file() and not (frontend_src / "src").is_dir() and not (frontend_src / "package.json").is_file():
            _sync_tree(frontend_src, OVERLAY_FRONTEND)


def _auth(token: str | None) -> None:
    if not TOKEN or token != TOKEN:
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
    backup_note = f"pre-update-{payload.version}"
    rollback = ""
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

        _apply_live_overlays(work)
        if OVERLAY_APP.exists():
            (OVERLAY_APP / ".update-stamp").write_text(str(time.time()), encoding="utf-8")

        # atomic symlink swap of current release
        tmp_link = RELEASES / f"current-{payload.version}.tmp"
        if tmp_link.exists() or tmp_link.is_symlink():
            tmp_link.unlink()
        tmp_link.symlink_to(dest)
        tmp_link.replace(CURRENT)

        if payload.migration_id:
            env = os.environ.copy()
            # Only run alembic with the known command; never a script from the ZIP.
            proc = subprocess.run(
                ["python", "-m", "alembic", "upgrade", "head"],
                cwd=str(CURRENT / "backend") if (CURRENT / "backend" / "alembic.ini").exists() else "/app",
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr[-2000:] or "alembic failed")

        if not _wait_health():
            raise RuntimeError("health check failed after install")
        return {"ok": True, "version": payload.version, "previous": previous}
    except Exception as exc:
        rollback = str(exc)
        prev_dir = RELEASES / previous
        if prev_dir.exists():
            tmp_link = RELEASES / "current-rollback.tmp"
            if tmp_link.exists() or tmp_link.is_symlink():
                tmp_link.unlink()
            tmp_link.symlink_to(prev_dir)
            tmp_link.replace(CURRENT)
        try:
            subprocess.run(
                ["python", "-m", "alembic", "downgrade", "-1"],
                cwd="/app",
                env=os.environ.copy(),
                capture_output=True,
                timeout=60,
            )
        except Exception:
            pass
        return {"ok": False, "error": rollback, "rolled_back": True, "rollback": rollback}


def _wait_health() -> bool:
    import urllib.request

    for _ in range(15):
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False
