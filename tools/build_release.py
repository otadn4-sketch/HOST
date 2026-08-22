#!/usr/bin/env python3
"""Build a signed Eytan release bundle.

Never put docker-compose.yml, install.sh, Dockerfiles, or secrets in the bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from nacl.signing import SigningKey

ALLOWED_ROOTS = ("frontend/dist", "backend/app", "backend/alembic/versions", "VERSION", "CHANGELOG.md", "docs/CHANGELOG.md")


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
    frontend_dist = root / "frontend" / "dist"
    if frontend_dist.exists():
        for p in frontend_dist.rglob("*"):
            if p.is_file():
                items.append((f"frontend/{p.relative_to(frontend_dist).as_posix()}", p))
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
    parser.add_argument("--version", required=True)
    parser.add_argument("--compatible-from", default="1.0.0")
    parser.add_argument("--migration-id", default="001_initial")
    parser.add_argument("--changelog", default="")
    parser.add_argument("--secret-key", required=True, help="path to offline ed25519.secret")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = collect(root)
    manifest_files = [{"path": rel, "sha256": sha256(path), "size": path.stat().st_size} for rel, path in files]
    manifest = {
        "name": "eytan-vault",
        "version": args.version,
        "compatible_from": args.compatible_from,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "migration_id": args.migration_id,
        "changelog": args.changelog,
        "files": manifest_files,
    }
    canonical = json.dumps({k: v for k, v in manifest.items() if k != "signature"}, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sk = SigningKey(Path(args.secret_key).read_bytes())
    manifest["signature"] = sk.sign(canonical).signature.hex()
    out = Path(args.out or f"dist/eytan-{args.version}.zip")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for rel, path in files:
            zf.write(path, rel)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
