from __future__ import annotations

SUPPORTED_RULES = (
    "strip_recipient_details",
    "remove_recommendation_sections",
    "strip_pdf_metadata",
    "strip_office_metadata",
)


def plan_scrub(rules: list[str] | None) -> dict:
    selected = [r for r in (rules or []) if r in SUPPORTED_RULES]
    if not selected:
        selected = list(SUPPORTED_RULES[:2])
    return {
        "status": "stub",
        "applied": False,
        "rules": selected,
        "note": "خط لوله پالایش سند در فاز ۵ به‌صورت stub است و فایل اصلی را تغییر نمی‌دهد.",
    }
