from __future__ import annotations

import hashlib
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
SKIP_DIR_PREFIXES = ("__macosx/",)


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


def _norm(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def _logical_name(name: str, prefix: str) -> str:
    n = _norm(name)
    if prefix and n.startswith(prefix):
        return n[len(prefix) :]
    return n


def is_payload_path(rel: str) -> bool:
    rel = _norm(rel)
    if not rel or rel.endswith("/"):
        return False
    lower = rel.lower()
    if lower.startswith(SKIP_DIR_PREFIXES) or Path(rel).name in {".DS_Store", "Thumbs.db"}:
        return False
    if Path(rel).name.lower() in FORBIDDEN_NAMES:
        return False
    if lower.endswith((".sh", ".exe", ".bat", ".ps1", ".com")):
        return False
    if rel in {"VERSION", "CHANGELOG.md", "manifest.json"}:
        return True
    return any(rel.startswith(p) for p in ("frontend/", "backend/app/", "backend/alembic/versions/"))


def detect_archive_prefix(names: list[str]) -> str:
    rels = [_norm(n) for n in names if _norm(n) and not _norm(n).endswith("/")]
    rels = [n for n in rels if not n.lower().startswith(SKIP_DIR_PREFIXES)]

    def rooted(items: list[str]) -> bool:
        return any(
            s == "manifest.json"
            or s == "VERSION"
            or s.startswith("backend/app/")
            or s.startswith("frontend/")
            for s in items
        )

    if rooted(rels):
        return ""
    tops = {n.split("/")[0] for n in rels if "/" in n}
    tops.discard("__MACOSX")
    if len(tops) == 1:
        top = next(iter(tops))
        stripped = [n[len(top) + 1 :] for n in rels if n.startswith(top + "/")]
        if rooted(stripped):
            return top + "/"
    for n in rels:
        if n.endswith("/manifest.json") or n.endswith("/VERSION"):
            return n.rsplit("/", 1)[0] + "/"
        marker = "/backend/app/"
        if marker in n:
            return n[: n.find(marker)] + "/"
    return ""


def _safety_errors(zf: zipfile.ZipFile) -> list[str]:
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
        name = _norm(info.filename)
        if name.startswith("/") or ".." in Path(name).parts:
            errors.append(f"illegal path: {name}")
        if info.file_size > MAX_FILE_SIZE:
            errors.append(f"file too large: {name}")
        is_symlink = (info.external_attr >> 16) & 0o170000 == 0o120000
        if is_symlink:
            errors.append(f"symlink forbidden: {name}")
    return errors


def validate_zip_members(zf: zipfile.ZipFile) -> list[str]:
    """Strict checks for signed release bundles."""
    errors = _safety_errors(zf)
    prefix = detect_archive_prefix([i.filename for i in zf.infolist()])
    for info in zf.infolist():
        name = _norm(info.filename)
        if name.endswith("/") or info.is_dir():
            continue
        logical = _logical_name(name, prefix)
        if not logical or logical.lower().startswith(SKIP_DIR_PREFIXES):
            continue
        if Path(logical).name.lower() in FORBIDDEN_NAMES:
            errors.append(f"forbidden file: {logical}")
        if not is_payload_path(logical) and Path(logical).name.lower() not in FORBIDDEN_NAMES:
            errors.append(f"path not allowed in release bundle: {logical}")
        if logical.lower().endswith((".sh", ".exe", ".bat", ".ps1", ".com")):
            errors.append(f"executable content forbidden: {logical}")
    return errors


def _read_manifest(zf: zipfile.ZipFile, prefix: str) -> tuple[dict[str, Any] | None, str | None]:
    candidates = []
    if prefix:
        candidates.append(prefix + "manifest.json")
    candidates.extend(["manifest.json"])
    names = {_norm(i.filename): i.filename for i in zf.infolist()}
    for cand in candidates:
        if cand in names:
            try:
                raw = zf.read(names[cand])
                return json.loads(raw.decode("utf-8")), None
            except Exception as exc:
                return None, f"manifest.json missing or invalid: {exc}"
    for stored, original in names.items():
        if stored.endswith("/manifest.json") or stored == "manifest.json":
            try:
                raw = zf.read(original)
                return json.loads(raw.decode("utf-8")), None
            except Exception as exc:
                return None, f"manifest.json missing or invalid: {exc}"
    return None, None


def _extract_payload(zf: zipfile.ZipFile, dest: Path, prefix: str) -> list[str]:
    extracted: list[str] = []
    dest.mkdir(parents=True, exist_ok=True)
    for info in zf.infolist():
        name = _norm(info.filename)
        if name.endswith("/") or info.is_dir():
            continue
        logical = _logical_name(name, prefix)
        if not is_payload_path(logical) or logical == "manifest.json":
            continue
        target = dest / logical
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, target.open("wb") as out:
            remaining = info.file_size
            while remaining > 0:
                chunk = src.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                out.write(chunk)
        extracted.append(logical)
    return extracted


def _synthetic_manifest(dest: Path, extracted: list[str], changelog: str = "") -> dict[str, Any]:
    version = "1.1.0"
    vfile = dest / "VERSION"
    if vfile.is_file():
        version = vfile.read_text(encoding="utf-8").strip() or version
    files = []
    for rel in extracted:
        path = dest / rel
        if path.is_file():
            files.append({"path": rel, "sha256": sha256_file(path), "size": path.stat().st_size})
    return {
        "name": "eytan-vault",
        "version": version,
        "compatible_from": "0.0.0",
        "migration_id": "",
        "changelog": changelog
        or "بسته منبع بارگذاری‌شده توسط مدیر سامانه (فایل‌های غیرمجاز نادیده گرفته شد).",
        "files": files,
        "unsigned_source": True,
    }


def _verify_listed_files(dest: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    expected_files = manifest.get("files") or []
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
        if listed and rel not in listed:
            errors.append(f"unlisted file extracted: {rel}")


def verify_and_extract(
    bundle: Path,
    public_key: str,
    dest: Path,
    allow_unsigned: bool = False,
) -> BundleValidation:
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    try:
        with zipfile.ZipFile(bundle) as zf:
            prefix = detect_archive_prefix([i.filename for i in zf.infolist()])
            loaded, manifest_err = _read_manifest(zf, prefix)
            if allow_unsigned:
                errors.extend(_safety_errors(zf))
            else:
                errors.extend(validate_zip_members(zf))

            if loaded is None:
                if not allow_unsigned:
                    return BundleValidation(
                        False,
                        {},
                        [
                            manifest_err
                            or "manifest.json missing or invalid: There is no item named 'manifest.json' in the archive"
                        ],
                    )
            else:
                manifest = loaded

            signature = (manifest or {}).get("signature") or ""
            key = (public_key or "").strip()
            if allow_unsigned and not signature:
                pass
            elif not key:
                errors.append("UPDATE_PUBLIC_KEY is not configured")
            elif not signature:
                errors.append("manifest signature missing")
            elif not manifest:
                errors.append("manifest.json missing or invalid")
            else:
                try:
                    vk = parse_public_key(key)
                    vk.verify(
                        _canonical_manifest(manifest),
                        bytes.fromhex(signature) if len(signature) == 128 else __import__("base64").b64decode(signature),
                    )
                except (BadSignatureError, Exception) as exc:
                    errors.append(f"invalid Ed25519 signature: {exc}")

            extracted = _extract_payload(zf, dest, prefix)
            if not extracted:
                errors.append("zip شامل فایل‌های قابل نصب سامانه (VERSION / backend/app / frontend) نیست.")

            if manifest.get("files"):
                _verify_listed_files(dest, manifest, errors)
            elif allow_unsigned:
                manifest = _synthetic_manifest(dest, extracted)
    except zipfile.BadZipFile:
        return BundleValidation(False, {}, ["bundle is not a valid zip"])

    if manifest:
        required = ["version", "compatible_from", "migration_id", "files"]
        for key_name in required:
            if key_name not in manifest:
                errors.append(f"manifest missing {key_name}")

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

    if not new_version or parts(new_version) == (0, 0, 0) and new_version not in {"0.0.0", "0.0", "0"}:
        return True
    return parts(compatible_from) <= parts(current) <= parts(new_version) or current == "0.0.0"
