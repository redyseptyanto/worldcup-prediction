"""State-aware feature refresh helpers."""

from __future__ import annotations

from src.features.build_features import build_feature_artifacts
from src.models.train import train_models


class FeatureUpdater:
    """Refresh feature artifacts and the ensemble."""

    def refresh(self) -> None:
        build_feature_artifacts()
        train_models(force=True)
