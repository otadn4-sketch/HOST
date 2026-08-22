#!/usr/bin/env python3
"""Pack an on-prem update zip with manifest.json at the archive root.

Usage:
  python tools/pack_update_zip.py --out dist/eytan-1.1.0.zip
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(root: Path) -> list[tuple[str, Path]]:
    items: list[tuple[str, Path]] = []
    version = root / "VERSION"
    changelog = root / "docs" / "CHANGELOG.md"
    if version.exists():
        items.append(("VERSION", version))
    if changelog.exists():
        items.append(("CHANGELOG.md", changelog))
    dist = root / "frontend" / "dist"
    frontend = root / "frontend"
    if dist.exists():
        for p in dist.rglob("*"):
            if p.is_file():
                items.append((f"frontend/{p.relative_to(dist).as_posix()}", p))
    elif frontend.exists():
        for p in frontend.rglob("*"):
            if p.is_file() and "node_modules" not in p.parts:
                items.append((f"frontend/{p.relative_to(frontend).as_posix()}", p))
    app_dir = root / "backend" / "app"
    for p in app_dir.rglob("*"):
        if p.is_file() and p.suffix != ".pyc":
            items.append((f"backend/app/{p.relative_to(app_dir).as_posix()}", p))
    mig = root / "backend" / "alembic" / "versions"
    if mig.exists():
        for p in mig.glob("*.py"):
            items.append((f"backend/alembic/versions/{p.name}", p))
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="dist/eytan-update.zip")
    parser.add_argument("--changelog", default="")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = collect(root)
    version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").exists() else "1.1.0"
    manifest = {
        "name": "eytan-vault",
        "version": version,
        "compatible_from": "0.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "migration_id": "001_initial",
        "changelog": args.changelog or f"بسته به‌روزرسانی {version}",
        "files": [{"path": rel, "sha256": sha256(path), "size": path.stat().st_size} for rel, path in files],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for rel, path in files:
            zf.write(path, rel)
    print(f"wrote {out} ({len(files)} files, version {version})")


if __name__ == "__main__":
    main()
