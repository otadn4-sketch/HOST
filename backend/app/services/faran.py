from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.models.entities import FaranSyncRecord, FileObject, utcnow


class FaranClient:
    """Modular Faran API client. Default is an offline stub (no outbound HTTP)."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.base_url = (self.settings.faran_base_url or "").rstrip("/")
        self.token = self.settings.faran_api_token or ""
        self.enabled = bool(self.settings.faran_enabled and self.base_url)
        self.allow_network = bool(self.settings.faran_allow_network)

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "configured": bool(self.base_url),
            "allow_network": self.allow_network,
            "mode": "stub",
            "base_url_set": bool(self.base_url),
            "capabilities": ["upload_metadata", "download", "daily_read", "import_excel_tags"],
            "note": (
                "اتصال زنده فاران هنوز سیم‌کشی نشده است. همگام‌سازی فعلی فقط رکورد stub می‌نویسد "
                "و درخواست شبکه نمی‌فرستد مگر اینکه FARAN_ALLOW_NETWORK فعال شود."
            ),
        }

    def file_payload(self, file: FileObject) -> dict:
        return {
            "local_id": file.id,
            "title": file.title,
            "original_name": file.original_name,
            "topic": file.topic,
            "tags": file.tags or [],
            "authors": file.authors or [],
            "excel_logged": file.excel_logged or {},
            "classification": file.classification,
            "sha256": file.sha256,
            "extension": file.extension,
            "faran_remote_id": file.faran_remote_id,
        }

    def ping(self) -> dict:
        if not self.enabled:
            return {"ok": False, "reason": "faran_disabled_or_unconfigured"}
        if not self.allow_network:
            return {"ok": False, "reason": "network_disabled_stub_only"}
        return {"ok": False, "reason": "live_client_not_wired"}

    def push_metadata(self, files: list[FileObject]) -> dict:
        items = [self.file_payload(f) for f in files]
        return {"ok": True, "mode": "stub", "queued": len(items), "items": items[:20]}

    def daily_read(self) -> dict:
        return {
            "ok": True,
            "mode": "stub",
            "fetched": 0,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "records": [],
        }


def record_sync(db, *, user_id: str | None, direction: str, result: dict, error: str = "") -> FaranSyncRecord:
    row = FaranSyncRecord(
        started_at=utcnow(),
        finished_at=utcnow(),
        status="stub" if not error else "error",
        direction=direction,
        items_count=int(result.get("queued") or result.get("fetched") or 0),
        error=error,
        actor_user_id=user_id,
        details={"mode": result.get("mode", "stub"), "ok": result.get("ok", False)},
    )
    db.add(row)
    db.flush()
    return row


FaranClient = FaranClient
record_sync = record_sync
