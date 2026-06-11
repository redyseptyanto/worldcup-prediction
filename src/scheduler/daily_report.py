"""Generate a lightweight daily markdown report."""

from __future__ import annotations

from src.config import SETTINGS
from src.utils.helpers import load_json, utc_timestamp


def generate_daily_report() -> str:
    """Write a short markdown report from the latest snapshot."""

    snapshots = sorted(path.name for path in SETTINGS.snapshots_dir.iterdir() if path.is_dir())
    latest = snapshots[-1] if snapshots else "none"
    latest_bracket = {}
    if latest != "none":
        latest_bracket = load_json(SETTINGS.snapshots_dir / latest / "bracket_data.json", default={})
    lines = [
        "# Daily Prediction Report",
        "",
        f"Generated at: {utc_timestamp()}",
        f"Latest snapshot: {latest}",
        "",
        "## Champion Odds",
        "",
    ]
    champion_odds = latest_bracket.get("champion_odds", {})
    if champion_odds:
        for team, probability in champion_odds.items():
            lines.append(f"- {team}: {probability:.3f}")
    else:
        lines.append("- No snapshot data available yet.")
    report_path = SETTINGS.reports_dir / "daily_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)
