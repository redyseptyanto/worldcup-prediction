from src.models.train import load_or_train_ensemble
from src.models.random_forest_model import RandomForestOutcomeModel
from src.models.xgboost_model import BoostedOutcomeModel
from src.utils.constants import OUTCOME_ORDER


def test_ensemble_prediction_probabilities_sum_to_one() -> None:
    model = load_or_train_ensemble(force=True)
    prediction = model.predict_match("Argentina", "Japan")
    probabilities = prediction["outcome_probabilities"]

    assert round(sum(probabilities.values()), 6) == 1.0
    assert prediction["confidence"]["overall"] > 0


def test_tree_models_use_fitted_feature_schema_for_prediction() -> None:
    model = load_or_train_ensemble(force=True)
    features = model.build_match_features("South Korea", "Czech Republic")

    legacy_feature_subset = {
        key: features[key]
        for key in [
            "elo_diff",
            "ranking_diff",
            "goals_for_diff",
            "goals_against_diff",
            "form_diff",
            "attack_diff",
            "defense_diff",
        ]
    }

    boosted = BoostedOutcomeModel()
    boosted.model = model.boosted.model
    rf = RandomForestOutcomeModel()
    rf.model = model.random_forest.model

    boosted_probs = boosted.predict_proba(legacy_feature_subset)
    rf_probs = rf.predict_proba(legacy_feature_subset)

    assert round(sum(boosted_probs.values()), 6) == 1.0
    assert round(sum(rf_probs.values()), 6) == 1.0


def test_representative_scoreline_matches_dominant_outcome() -> None:
    model = load_or_train_ensemble(force=True)
    score = model._representative_scoreline(  # noqa: SLF001 - targeted regression for displayed scoreline logic.
        {"home": 1.633, "away": 1.536},
        dict(zip(OUTCOME_ORDER, [0.6093, 0.2006, 0.1901])),
    )

    assert score == {"home": 2, "away": 1}


def test_most_likely_exact_scoreline_uses_full_score_distribution() -> None:
    model = load_or_train_ensemble(force=True)
    score = model._most_likely_exact_scoreline({"home": 1.633, "away": 1.536})  # noqa: SLF001 - targeted regression for exact-score display.

    assert score["home"] == 1
    assert score["away"] == 1
    assert score["probability"] > 0.10
