"""Snapshot comparison helpers."""

from __future__ import annotations

from typing import Any

from src.config import EVOLUTION_REPORT_FILE
from src.utils.helpers import save_json


class SnapshotComparer:
    """Compare snapshot outputs and write an evolution report."""

    def compare(self, from_snapshot: str, to_snapshot: str, from_payload: dict[str, Any], to_payload: dict[str, Any]) -> dict[str, Any]:
        champion_before = from_payload["bracket_data"]["champion_odds"]
        champion_after = to_payload["bracket_data"]["champion_odds"]
        movers = []
        for team in sorted(set(champion_before) | set(champion_after)):
            before = champion_before.get(team, 0.0)
            after = champion_after.get(team, 0.0)
            movers.append({"team": team, "before": before, "after": after, "delta": round(after - before, 4)})
        movers.sort(key=lambda row: abs(row["delta"]), reverse=True)
        result = {"from_snapshot": from_snapshot, "to_snapshot": to_snapshot, "champion_odds_delta": movers}
        return result

    def write_report(self, comparison: dict[str, Any]) -> str:
        lines = [
            "# Snapshot Evolution Report",
            "",
            f"From: {comparison['from_snapshot']}",
            f"To: {comparison['to_snapshot']}",
            "",
            "## Champion Odds Delta",
            "",
        ]
        for row in comparison["champion_odds_delta"]:
            lines.append(f"- {row['team']}: {row['before']:.3f} -> {row['after']:.3f} (delta {row['delta']:+.3f})")
        EVOLUTION_REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
        return str(EVOLUTION_REPORT_FILE)
