"""Project configuration and filesystem paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Centralized project settings."""

    root_dir: Path
    data_dir: Path
    raw_dir: Path
    processed_dir: Path
    features_dir: Path
    datasets_dir: Path
    external_dir: Path
    models_dir: Path
    output_dir: Path
    snapshots_dir: Path
    reports_dir: Path
    state_dir: Path
    flags_dir: Path
    random_seed: int = 42
    default_iterations: int = 1000


ROOT_DIR = Path(__file__).resolve().parent.parent

SETTINGS = Settings(
    root_dir=ROOT_DIR,
    data_dir=ROOT_DIR / "data",
    raw_dir=ROOT_DIR / "data" / "raw",
    processed_dir=ROOT_DIR / "data" / "processed",
    features_dir=ROOT_DIR / "data" / "processed" / "features",
    datasets_dir=ROOT_DIR / "data" / "processed" / "datasets",
    external_dir=ROOT_DIR / "data" / "external",
    models_dir=ROOT_DIR / "models",
    output_dir=ROOT_DIR / "output",
    snapshots_dir=ROOT_DIR / "output" / "snapshots",
    reports_dir=ROOT_DIR / "output" / "reports",
    state_dir=ROOT_DIR / "output" / "state",
    flags_dir=ROOT_DIR / "data" / "raw" / "flags",
)


RAW_MATCHES_FILE = SETTINGS.raw_dir / "matches" / "historical_matches.csv"
RAW_PENALTIES_FILE = SETTINGS.raw_dir / "matches" / "historical_penalties.csv"
RAW_RANKINGS_FILE = SETTINGS.raw_dir / "rankings" / "team_rankings.csv"
RAW_FIXTURES_FILE = SETTINGS.raw_dir / "fixtures" / "worldcup_fixtures.csv"
RAW_THIRD_PLACE_MAPPING_FILE = SETTINGS.raw_dir / "fixtures" / "third_place_mapping.json"
RAW_SOFIFA_PLAYERS_FILE = SETTINGS.raw_dir / "players" / "sofifa_players.csv"
RAW_TRANSFERMARKT_PROFILES_FILE = SETTINGS.raw_dir / "players" / "transfermarkt_player_profiles.csv"
RAW_TRANSFERMARKT_VALUES_FILE = SETTINGS.raw_dir / "players" / "transfermarkt_player_values.csv"
RAW_TRANSFERMARKT_INJURIES_FILE = SETTINGS.raw_dir / "players" / "transfermarkt_player_injuries.csv"
RAW_TRANSFERMARKT_NATIONAL_FILE = SETTINGS.raw_dir / "players" / "transfermarkt_player_national_performances.csv"
RAW_MACRO_FILE = SETTINGS.raw_dir / "macro" / "world_bank_macro.csv"
RAW_WEATHER_FILE = SETTINGS.raw_dir / "weather" / "fixture_weather.csv"
FLAGS_DIR = SETTINGS.flags_dir
AUTO_RESULTS_FILE = SETTINGS.external_dir / "auto_results.csv"
TRAIN_DATASET_FILE = SETTINGS.datasets_dir / "train.csv"
TEAM_FEATURES_FILE = SETTINGS.features_dir / "team_features.json"
ROSTERS_FILE = SETTINGS.features_dir / "rosters.json"
FIXTURE_CONTEXT_FILE = SETTINGS.features_dir / "fixture_context.json"
ENSEMBLE_MODEL_FILE = SETTINGS.models_dir / "ensemble.pkl"
MODEL_METRICS_FILE = SETTINGS.models_dir / "metrics.json"
MODEL_WEIGHTS_FILE = SETTINGS.models_dir / "ensemble_weights.json"
PREDICTIONS_FILE = SETTINGS.output_dir / "predictions.csv"
SIMULATION_RESULTS_FILE = SETTINGS.output_dir / "simulation_results.json"
EVOLUTION_REPORT_FILE = SETTINGS.output_dir / "evolution_report.md"
MATCH_STATE_FILE = SETTINGS.state_dir / "matches.json"
LEDGER_FILE = SETTINGS.output_dir / "prediction_ledger.csv"


def ensure_directories() -> None:
    """Create the directory structure required by the baseline pipeline."""

    for path in (
        SETTINGS.data_dir,
        SETTINGS.raw_dir / "matches",
        SETTINGS.raw_dir / "rankings",
        SETTINGS.raw_dir / "fixtures",
        SETTINGS.raw_dir / "players",
        SETTINGS.raw_dir / "macro",
        SETTINGS.raw_dir / "weather",
        SETTINGS.flags_dir,
        SETTINGS.processed_dir,
        SETTINGS.features_dir,
        SETTINGS.datasets_dir,
        SETTINGS.external_dir,
        SETTINGS.models_dir,
        SETTINGS.output_dir,
        SETTINGS.snapshots_dir,
        SETTINGS.reports_dir,
        SETTINGS.state_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
