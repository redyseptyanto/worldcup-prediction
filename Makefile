PYTHON ?= python
ITERATIONS ?= 500
match_id ?=
score ?=
file ?=
snapshot ?=
from ?=
to ?=

.PHONY: collect-data engineer-features train-models simulate predict serve-api serve-dashboard run-all test clean ingest-result ingest-batch snapshot-real-groups tournament-status compare-snapshots evolution-report update-bracket rollback-to scheduler-run-now visualize-all visualize-bracket visualize-standings visualize-compare

collect-data:
	$(PYTHON) -m src.data.collector --all

engineer-features:
	$(PYTHON) -m src.features.build_features

train-models:
	$(PYTHON) -m src.models.train --all

simulate:
	$(PYTHON) -m src.simulation.tournament --iterations $(ITERATIONS)

predict:
	$(PYTHON) -m src.simulation.tournament --iterations $(ITERATIONS)

serve-api:
	$(PYTHON) -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

serve-dashboard:
	$(PYTHON) -m streamlit run src/visualization/dashboard.py

run-all:
	$(PYTHON) -m src.data.collector --all
	$(PYTHON) -m src.features.build_features
	$(PYTHON) -m src.models.train --all
	$(PYTHON) -m src.simulation.tournament --iterations $(ITERATIONS)

test:
	$(PYTHON) -m pytest tests -q

clean:
	$(PYTHON) -c "from pathlib import Path; import shutil; [shutil.rmtree(path, ignore_errors=True) for path in [Path('data/processed'), Path('models'), Path('output')]]"

ingest-result:
	$(PYTHON) -c "from src.adaptive.engine import AdaptiveEngine; home, away = '$(score)'.split('-'); print(AdaptiveEngine().ingest_result('$(match_id)', int(home), int(away)))"

ingest-batch:
	$(PYTHON) -c "from src.adaptive.engine import AdaptiveEngine; print(AdaptiveEngine().ingest_csv('$(file)'))"

snapshot-real-groups:
	$(PYTHON) scripts/ingest_group_stage.py

tournament-status:
	$(PYTHON) -c "from src.adaptive.engine import AdaptiveEngine; print(AdaptiveEngine().tournament_status())"

compare-snapshots:
	$(PYTHON) -c "from src.adaptive.engine import AdaptiveEngine; import sys; print(AdaptiveEngine().compare_snapshots('$(from)', '$(to)'))"

evolution-report:
	$(PYTHON) -c "from src.adaptive.engine import AdaptiveEngine; engine = AdaptiveEngine(); snaps = engine.snapshot_manager.list_snapshots(); print(engine.compare_snapshots(snaps[-2], snaps[-1]) if len(snaps) > 1 else 'Need at least two snapshots.')"

update-bracket:
	$(PYTHON) -c "from src.simulation.tournament import TournamentSimulator; print(TournamentSimulator().run())"

rollback-to:
	$(PYTHON) -c "from src.adaptive.engine import AdaptiveEngine; print(AdaptiveEngine().rollback_to('$(snapshot)'))"

scheduler-run-now:
	$(PYTHON) -m src.scheduler.daily_run

visualize-all:
	$(PYTHON) -c "from src.visualization.bracket import load_latest_bracket; from src.visualization.standings import load_latest_standings; print({'bracket': load_latest_bracket(), 'standings': load_latest_standings()})"

visualize-bracket:
	$(PYTHON) -c "from src.visualization.bracket import load_latest_bracket; print(load_latest_bracket())"

visualize-standings:
	$(PYTHON) -c "from src.visualization.standings import load_latest_standings; print(load_latest_standings())"

visualize-compare:
	$(PYTHON) -c "from src.visualization.comparison_view import compare_snapshots; print(compare_snapshots('$(from)', '$(to)'))"
