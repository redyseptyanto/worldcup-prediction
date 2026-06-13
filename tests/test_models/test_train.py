from pathlib import Path

from src.models.train import load_or_train_ensemble


def test_load_or_train_rebuilds_when_saved_model_is_incompatible(monkeypatch, tmp_path: Path) -> None:
    model_file = tmp_path / "ensemble.pkl"
    model_file.write_bytes(b"legacy")
    rebuilt_model = object()

    monkeypatch.setattr("src.models.train.ensure_sample_data", lambda: None)
    monkeypatch.setattr("src.models.train.ENSEMBLE_MODEL_FILE", model_file)

    def broken_load() -> object:
        raise TypeError("legacy pickle")

    monkeypatch.setattr("src.models.train.EnsembleModel.load", broken_load)
    monkeypatch.setattr("src.models.train.train_models", lambda force=False: rebuilt_model)

    assert load_or_train_ensemble() is rebuilt_model
