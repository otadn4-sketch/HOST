from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

ALLOWED_PREFIXES = (
    "frontend/",
    "backend/app/",
    "backend/alembic/versions/",
    "VERSION",
    "CHANGELOG.md",
    "manifest.json",
)

FORBIDDEN_NAMES = {
    "install.sh",
    "docker-compose.yml",
    "docker-compose.yaml",
    "dockerfile",
    "compose.yml",
    ".env",
    ".env.local",
}

MAX_FILES = 4000
MAX_UNCOMPRESSED = 400 * 1024 * 1024
MAX_RATIO = 80
MAX_FILE_SIZE = 80 * 1024 * 1024


@dataclass
class BundleValidation:
    ok: bool
    manifest: dict[str, Any]
    errors: list[str]
    extracted_dir: Path | None = None


def _canonical_manifest(manifest: dict[str, Any]) -> bytes:
    body = {k: v for k, v in manifest.items() if k != "signature"}
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def parse_public_key(value: str) -> VerifyKey:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("UPDATE_PUBLIC_KEY is not configured")
    if len(raw) == 64:
        return VerifyKey(bytes.fromhex(raw))
    import base64

    return VerifyKey(base64.b64decode(raw))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_zip_members(zf: zipfile.ZipFile) -> list[str]:
    errors: list[str] = []
    infos = zf.infolist()
    if len(infos) > MAX_FILES:
        errors.append("too many files in bundle")
    uncompressed = sum(i.file_size for i in infos)
    compressed = sum(i.compress_size or 1 for i in infos)
    if uncompressed > MAX_UNCOMPRESSED:
        errors.append("uncompressed size exceeds limit")
    if compressed and uncompressed / max(compressed, 1) > MAX_RATIO:
        errors.append("compression ratio looks like a zip bomb")
    for info in infos:
        name = info.filename.replace("\\", "/")
        lower = Path(name).name.lower()
        if name.startswith("/") or name.startswith("\\") or ".." in Path(name).parts:
            errors.append(f"illegal path: {name}")
        if info.file_size > MAX_FILE_SIZE:
            errors.append(f"file too large: {name}")
        is_symlink = (info.external_attr >> 16) & 0o170000 == 0o120000
        if is_symlink:
            errors.append(f"symlink forbidden: {name}")
        if lower in FORBIDDEN_NAMES:
            errors.append(f"forbidden file: {name}")
        if name.endswith("/") or info.is_dir():
            continue
        allowed = name == "manifest.json" or any(
            name == prefix.rstrip("/") or name.startswith(prefix) for prefix in ALLOWED_PREFIXES
        )
        if not allowed:
            errors.append(f"path not allowed in release bundle: {name}")
        if name.lower().endswith((".sh", ".exe", ".bat", ".ps1", ".com")):
            errors.append(f"executable content forbidden: {name}")
    return errors


def verify_and_extract(bundle: Path, public_key: str, dest: Path) -> BundleValidation:
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    try:
        with zipfile.ZipFile(bundle) as zf:
            errors.extend(validate_zip_members(zf))
            try:
                raw_manifest = zf.read("manifest.json")
                manifest = json.loads(raw_manifest.decode("utf-8"))
            except Exception as exc:
                return BundleValidation(False, {}, [f"manifest.json missing or invalid: {exc}"])

            signature = manifest.get("signature") or ""
            try:
                vk = parse_public_key(public_key)
                vk.verify(_canonical_manifest(manifest), bytes.fromhex(signature) if len(signature) == 128 else __import__("base64").b64decode(signature))
            except (BadSignatureError, Exception) as exc:
                errors.append(f"invalid Ed25519 signature: {exc}")

            dest.mkdir(parents=True, exist_ok=True)
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                if name.endswith("/") or info.is_dir():
                    continue
                target = dest / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, target.open("wb") as out:
                    remaining = info.file_size
                    while remaining > 0:
                        chunk = src.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        out.write(chunk)

            expected_files = manifest.get("files") or []
            if len(expected_files) != len([p for p in dest.rglob("*") if p.is_file() and p.name != "manifest.json"]) and False:
                pass
            listed = {item["path"]: item for item in expected_files}
            for rel, meta in listed.items():
                file_path = dest / rel
                if not file_path.is_file():
                    errors.append(f"missing listed file: {rel}")
                    continue
                digest = sha256_file(file_path)
                if digest != meta.get("sha256"):
                    errors.append(f"hash mismatch: {rel}")
                if int(meta.get("size") or 0) != file_path.stat().st_size:
                    errors.append(f"size mismatch: {rel}")
            for path in dest.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(dest).as_posix()
                if rel == "manifest.json":
                    continue
                if rel not in listed:
                    errors.append(f"unlisted file extracted: {rel}")
    except zipfile.BadZipFile:
        return BundleValidation(False, {}, ["bundle is not a valid zip"])

    required = ["version", "compatible_from", "migration_id", "files"]
    for key in required:
        if key not in manifest:
            errors.append(f"manifest missing {key}")

    return BundleValidation(ok=not errors, manifest=manifest, errors=errors, extracted_dir=dest)


def current_version(root: Path) -> str:
    version_file = root / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


def is_compatible(current: str, compatible_from: str, new_version: str) -> bool:
    def parts(v: str) -> tuple[int, int, int]:
        nums = []
        for piece in v.split("."):
            try:
                nums.append(int(piece))
            except ValueError:
                nums.append(0)
        while len(nums) < 3:
            nums.append(0)
        return nums[0], nums[1], nums[2]

    return parts(compatible_from) <= parts(current) <= parts(new_version) or current == "0.0.0"
