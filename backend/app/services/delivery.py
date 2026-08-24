"""Deprecated automated delivery.

This product no longer sends download links or files through messengers or SMS.
All handoffs must be recorded with the Phase 1 manual transaction log.
"""

from __future__ import annotations


class AutomatedDeliveryService:
    enabled = False

    def send_link(self, *args, **kwargs):  # noqa: ARG002
        raise RuntimeError("ارسال خودکار لینک/فایل از طریق پیام‌رسان یا پیامک منسوخ و غیرفعال است.")

    def send_file(self, *args, **kwargs):  # noqa: ARG002
        raise RuntimeError("ارسال خودکار لینک/فایل از طریق پیام‌رسان یا پیامک منسوخ و غیرفعال است.")
