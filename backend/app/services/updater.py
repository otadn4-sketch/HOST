from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path


def app_root() -> Path:
    return Path(os.environ.get("EYTAN_APP_ROOT", "/app"))


def frontend_overlay() -> Path:
    return Path(os.environ.get("OVERLAY_FRONTEND_PATH", "/overlay/frontend"))


def merge_tree(src: Path, dest: Path) -> int:
    """Copy files from src into dest without deleting extra files already on disk."""
    copied = 0
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(src)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        copied += 1
    return copied


def apply_extracted_release(work: Path) -> list[str]:
    notes: list[str] = []
    root = app_root()
    if not root.exists():
        raise RuntimeError(f"مسیر اجرای سامانه پیدا نشد: {root}")

    app_src = work / "backend" / "app"
    if app_src.is_dir():
        count = merge_tree(app_src, root / "app")
        notes.append(f"backend/app ({count} فایل)")
    else:
        raise RuntimeError("بسته شامل backend/app نیست.")

    versions_src = work / "backend" / "alembic" / "versions"
    versions_dest = root / "alembic" / "versions"
    if versions_src.is_dir() and versions_dest.parent.exists():
        count = merge_tree(versions_src, versions_dest)
        notes.append(f"alembic/versions ({count} فایل)")

    version_src = work / "VERSION"
    if version_src.is_file():
        shutil.copy2(version_src, root / "VERSION")
        notes.append(f"VERSION={version_src.read_text(encoding='utf-8').strip()}")

    dist = work / "frontend" / "dist"
    fe = frontend_overlay()
    if dist.is_dir() and (dist / "index.html").is_file() and fe.exists():
        count = merge_tree(dist, fe)
        notes.append(f"frontend/dist ({count} فایل)")
    elif (work / "frontend" / "index.html").is_file() and not (work / "frontend" / "src").is_dir() and fe.exists():
        count = merge_tree(work / "frontend", fe)
        notes.append(f"frontend ({count} فایل)")
    else:
        notes.append("رابط کاربری در این بسته dist آماده نداشت؛ فقط بک‌اند اعمال شد.")
    return notes


def maybe_upgrade_alembic() -> str:
    ini = app_root() / "alembic.ini"
    if not ini.is_file():
        return "alembic موجود نیست؛ نادیده گرفته شد."
    try:
        proc = subprocess.run(
            ["python", "-m", "alembic", "upgrade", "head"],
            cwd=str(ini.parent),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()[-1500:]
        if proc.returncode != 0:
            return f"alembic هشدار (نصب ادامه یافت): {output or 'failed'}"
        return "alembic ok"
    except Exception as exc:
        return f"alembic نادیده گرفته شد: {exc}"


def write_reload_stamp() -> None:
    stamp = app_root() / ".update-stamp"
    try:
        stamp.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def delayed_reload_stamp(delay_seconds: float | None = None) -> None:
    if delay_seconds is None:
        delay_seconds = 0 if os.environ.get("EYTAN_ENV", "").lower() == "development" else 2.0
    if delay_seconds:
        time.sleep(delay_seconds)
    write_reload_stamp()
