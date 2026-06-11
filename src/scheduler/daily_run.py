"""Scheduler entry point."""

from __future__ import annotations

from src.scheduler.auto_ingester import run_auto_ingest
from src.scheduler.daily_report import generate_daily_report
from src.scheduler.notifier import notify


def run_daily() -> dict[str, object]:
    """Run the baseline daily automation flow."""

    ingest = run_auto_ingest()
    report = generate_daily_report()
    notification = notify(report)
    return {"ingest": ingest, "report": report, "notification": notification}


if __name__ == "__main__":
    print(run_daily())
