from src.models.train import load_or_train_ensemble


def test_ensemble_prediction_probabilities_sum_to_one() -> None:
    model = load_or_train_ensemble(force=True)
    prediction = model.predict_match("Argentina", "Japan")
    probabilities = prediction["outcome_probabilities"]

    assert round(sum(probabilities.values()), 6) == 1.0
    assert prediction["confidence"]["overall"] > 0
