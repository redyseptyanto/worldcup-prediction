"""Placeholder scraper layer for the offline baseline."""

from __future__ import annotations

from typing import Any


def fetch_placeholder_source(name: str) -> dict[str, Any]:
    """Return a placeholder record for future live integrations."""

    return {"source": name, "status": "offline-demo"}
