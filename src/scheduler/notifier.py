"""Notification stub for future integrations."""

from __future__ import annotations


def notify(report_path: str) -> dict[str, str]:
    """Return a no-op notification response."""

    return {"status": "skipped", "report_path": report_path}
