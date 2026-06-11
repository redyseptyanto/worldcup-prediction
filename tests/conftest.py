from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.config import ensure_directories
from src.data.collector import collect_all


@pytest.fixture(autouse=True)
def reset_generated_artifacts() -> None:
    root = Path(__file__).resolve().parent.parent
    for relative in ("data/processed", "models", "output"):
        shutil.rmtree(root / relative, ignore_errors=True)
    ensure_directories()
    collect_all()
