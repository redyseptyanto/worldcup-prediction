"""Full tournament orchestration."""

from __future__ import annotations

import argparse
from typing import Any

import pandas as pd

from src.config import PREDICTIONS_FILE, SETTINGS, SIMULATION_RESULTS_FILE
from src.data.loaders import load_fixtures
from src.models.train import load_or_train_ensemble
from src.simulation.group_stage import simulate_group_stage
from src.simulation.knockout_stage import simulate_knockout_stage
from src.utils.helpers import save_json
from src.utils.logger import get_logger

LOGGER = get_logger(__name__)


class TournamentSimulator:
    """Generate predictions and tournament odds."""

    def __init__(self, iterations: int = SETTINGS.default_iterations) -> None:
        self.iterations = iterations
        self.model = load_or_train_ensemble()
        self.fixtures = load_fixtures()

    def _predict_group_matches(self) -> list[dict[str, Any]]:
        rows = []
        for row in self.fixtures.itertuples(index=False):
            prediction = self.model.predict_match(row.home_team, row.away_team, match_id=row.match_id)
            rows.append(
                {
                    "match_id": row.match_id,
                    "stage": row.stage,
                    "group": row.group,
                    "home_team": row.home_team,
                    "away_team": row.away_team,
                    "host_city": getattr(row, "host_city", ""),
                    "predicted_home_goals": prediction["predicted_score"]["home"],
                    "predicted_away_goals": prediction["predicted_score"]["away"],
                    "home_win_probability": round(prediction["outcome_probabilities"]["home_win"], 4),
                    "draw_probability": round(prediction["outcome_probabilities"]["draw"], 4),
                    "away_win_probability": round(prediction["outcome_probabilities"]["away_win"], 4),
                    "confidence": prediction["confidence"]["overall"],
                    "confidence_label": prediction["confidence"]["label"],
                    "weather_temperature": prediction["contextual_factors"].get("weather_temperature"),
                    "weather_precipitation": prediction["contextual_factors"].get("weather_precipitation"),
                    "weather_wind": prediction["contextual_factors"].get("weather_wind"),
                    "rest_days_diff": prediction["contextual_factors"].get("rest_days_diff"),
                    "travel_fatigue_diff": prediction["contextual_factors"].get("travel_fatigue_diff"),
                }
            )
        return rows

    def run(self, resolved_results: dict[str, dict[str, int]] | None = None) -> dict[str, Any]:
        """Run the full baseline tournament workflow."""

        group_results = simulate_group_stage(
            self.fixtures,
            self.model,
            iterations=self.iterations,
            seed=SETTINGS.random_seed,
            resolved_results=resolved_results,
        )
        knockout_results = simulate_knockout_stage(
            self.model,
            group_results["standings"],
            iterations=self.iterations,
            seed=SETTINGS.random_seed + 1,
        )
        predictions = self._predict_group_matches()
        pd.DataFrame(predictions).to_csv(PREDICTIONS_FILE, index=False)
        output = {
            "iterations": self.iterations,
            "group_stage": group_results,
            "knockout": knockout_results,
            "predictions": predictions,
        }
        save_json(SIMULATION_RESULTS_FILE, output)
        LOGGER.info("Tournament simulation complete.")
        return output


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="Run the baseline tournament simulator.")
    parser.add_argument("--iterations", type=int, default=SETTINGS.default_iterations)
    args = parser.parse_args()
    simulator = TournamentSimulator(iterations=args.iterations)
    simulator.run()


if __name__ == "__main__":
    main()
