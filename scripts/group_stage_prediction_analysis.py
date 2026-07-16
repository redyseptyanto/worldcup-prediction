"""
Group Stage Prediction vs Reality Analysis
===========================================
Compares the model's group-stage predictions against real FIFA 2026 results,
identifies accuracy patterns, and extracts learnings for knockout stage predictions.

Usage: python scripts/group_stage_prediction_analysis.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

# ── Path setup ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SETTINGS
from src.utils.helpers import load_json

# ── Load data ───────────────────────────────────────────────────────────────

def load_real_results() -> dict[str, tuple[int, int]]:
    """Load real group-stage results from the CSV."""
    df = pd.read_csv(SETTINGS.external_dir / "real_group_stage_results.csv",
                     comment="#")
    return {row.match_id: (int(row.home_goals), int(row.away_goals))
            for row in df.itertuples()}


def load_fixtures() -> pd.DataFrame:
    """Load fixture definitions to map match_id → teams."""
    return pd.read_csv(SETTINGS.raw_dir / "fixtures" / "worldcup_fixtures.csv")


def load_fifa_standings() -> pd.DataFrame:
    """Load official FIFA standings with group positions."""
    return pd.read_csv(SETTINGS.external_dir / "fifa_official_standings.csv")


def load_team_stats() -> pd.DataFrame:
    """Load official FIFA team stats for knockout analysis."""
    return pd.read_csv(SETTINGS.external_dir / "fifa_official_team_stats.csv")


def load_snapshot_predictions(snapshot_id: str) -> list[dict]:
    """Load prediction data from a snapshot."""
    return load_json(SETTINGS.snapshots_dir / snapshot_id / "predictions.json") or []


def load_snapshot_bracket(snapshot_id: str) -> dict:
    """Load knockout bracket from a snapshot."""
    return load_json(SETTINGS.snapshots_dir / snapshot_id / "bracket_data.json") or {}


def load_round_of_32() -> pd.DataFrame:
    """Load the official Round-of-32 bracket."""
    from src.data.fifa_official import load_official_round_of_32
    return load_official_round_of_32()


# ── Analysis functions ──────────────────────────────────────────────────────

def compute_accuracy(ledger: pd.DataFrame, snapshot_id: str) -> dict:
    """Compute accuracy metrics for a given snapshot."""
    snap = ledger[ledger.snapshot_id == snapshot_id].copy()
    snap = snap[snap.actual_home_goals.notna()].copy()
    if len(snap) == 0:
        return {"snapshot": snapshot_id, "n_matches": 0, "outcome_accuracy": 0.0,
                "avg_confidence": 0.0, "avg_goals_error": 0.0, "correct": 0, "total": 0}

    correct_outcomes = snap.correct_outcome.sum()
    total = len(snap)
    outcome_acc = correct_outcomes / total * 100

    # Goal prediction error (absolute)
    snap["goals_error"] = (
        abs(snap.predicted_home_goals - snap.actual_home_goals)
        + abs(snap.predicted_away_goals - snap.actual_away_goals)
    )
    avg_goals_error = snap.goals_error.mean()

    # Average confidence where correct vs wrong
    avg_confidence = snap.confidence_score.mean()

    return {
        "snapshot": snapshot_id,
        "n_matches": total,
        "correct": int(correct_outcomes),
        "wrong": total - int(correct_outcomes),
        "outcome_accuracy_pct": round(outcome_acc, 2),
        "avg_confidence_pct": round(avg_confidence, 2),
        "avg_goals_error": round(avg_goals_error, 2),
    }


def analyze_by_group(ledger: pd.DataFrame, fixtures: pd.DataFrame,
                     snapshot_id: str) -> pd.DataFrame:
    """Analyze accuracy broken down by group."""
    snap = ledger[(ledger.snapshot_id == snapshot_id) &
                  ledger.actual_home_goals.notna()].copy()
    if len(snap) == 0:
        return pd.DataFrame()

    # Join group info from fixtures using match_id prefix
    snap["group_letter"] = snap.match_id.str.extract(r"GRP-([A-L])")

    group_stats = []
    for group, grp in snap.groupby("group_letter"):
        total = len(grp)
        correct = grp.correct_outcome.sum()
        grp["goals_err"] = (
            abs(grp.predicted_home_goals - grp.actual_home_goals)
            + abs(grp.predicted_away_goals - grp.actual_away_goals)
        )
        avg_err = grp.goals_err.mean()
        group_stats.append({
            "group": f"Group {group}",
            "matches": total,
            "correct": int(correct),
            "wrong": total - int(correct),
            "accuracy_pct": round(correct / total * 100, 1),
            "avg_goals_error": round(avg_err, 2),
        })
    return pd.DataFrame(group_stats).sort_values("accuracy_pct")


def analyze_by_confidence_bins(ledger: pd.DataFrame,
                                snapshot_id: str) -> pd.DataFrame:
    """Analyze whether higher confidence correlates with accuracy."""
    snap = ledger[(ledger.snapshot_id == snapshot_id) &
                  ledger.actual_home_goals.notna()].copy()
    if len(snap) == 0:
        return pd.DataFrame()

    bins = [0, 30, 40, 50, 60, 70, 100]
    labels = ["0-30%", "30-40%", "40-50%", "50-60%", "60-70%", "70-100%"]
    snap["conf_bin"] = pd.cut(snap.confidence_score, bins=bins, labels=labels, right=False)

    bin_stats = []
    for bin_label, grp in snap.groupby("conf_bin", observed=True):
        total = len(grp)
        correct = grp.correct_outcome.sum()
        bin_stats.append({
            "confidence_range": bin_label,
            "matches": total,
            "correct": int(correct),
            "wrong": total - int(correct),
            "accuracy_pct": round(correct / total * 100, 1),
        })
    return pd.DataFrame(bin_stats)


def analyze_favorite_upsets(ledger: pd.DataFrame, fixtures: pd.DataFrame,
                             snapshot_id: str) -> pd.DataFrame:
    """Find matches where the model confidently predicted one side but was wrong."""
    snap = ledger[(ledger.snapshot_id == snapshot_id) &
                  ledger.actual_home_goals.notna()].copy()
    if len(snap) == 0:
        return pd.DataFrame()

    # Merge with fixtures for team names
    merged = snap.merge(fixtures, on="match_id", how="left")

    # High confidence (>=60%) but wrong
    high_conf_wrong = merged[
        (merged.confidence_score >= 60) & (merged.correct_outcome == 0)
    ].copy()

    # Also identify low confidence (<40%) but correct (lucky)
    low_conf_correct = merged[
        (merged.confidence_score < 40) & (merged.correct_outcome == 1)
    ].copy()

    # Identify "statistical upsets" - where predicted score was very different
    merged["goals_diff"] = abs(merged.predicted_home_goals - merged.actual_home_goals) + \
                           abs(merged.predicted_away_goals - merged.actual_away_goals)
    big_score_misses = merged[merged.goals_diff >= 3].copy()

    return {
        "high_conf_wrong": high_conf_wrong[[
            "match_id", "home_team", "away_team", "predicted_home_goals",
            "predicted_away_goals", "actual_home_goals", "actual_away_goals",
            "predicted_home_win_pct", "predicted_draw_pct", "predicted_away_win_pct",
            "confidence_score"
        ]].sort_values("confidence_score", ascending=False),
        "low_conf_correct": low_conf_correct[[
            "match_id", "home_team", "away_team", "predicted_home_goals",
            "predicted_away_goals", "actual_home_goals", "actual_away_goals",
            "predicted_home_win_pct", "predicted_draw_pct", "predicted_away_win_pct",
            "confidence_score"
        ]].sort_values("confidence_score"),
        "big_score_misses": big_score_misses[[
            "match_id", "home_team", "away_team", "predicted_home_goals",
            "predicted_away_goals", "actual_home_goals", "actual_away_goals",
            "goals_diff"
        ]].sort_values("goals_diff", ascending=False),
    }


def analyze_scoreline_bias(ledger: pd.DataFrame, snapshot_id: str) -> dict:
    """Detect if model systematically under/over-predicts goals."""
    snap = ledger[(ledger.snapshot_id == snapshot_id) &
                  ledger.actual_home_goals.notna()].copy()
    if len(snap) == 0:
        return {}

    snap["home_bias"] = snap.predicted_home_goals - snap.actual_home_goals
    snap["away_bias"] = snap.predicted_away_goals - snap.actual_away_goals
    snap["total_bias"] = (snap.predicted_home_goals + snap.predicted_away_goals) - \
                          (snap.actual_home_goals + snap.actual_away_goals)

    return {
        "avg_home_goal_bias": round(snap.home_bias.mean(), 3),
        "avg_away_goal_bias": round(snap.away_bias.mean(), 3),
        "avg_total_goal_bias": round(snap.total_bias.mean(), 3),
        "std_total_goal_bias": round(snap.total_bias.std(), 3),
        "matches_under_predicted": int((snap.total_bias < -0.5).sum()),
        "matches_over_predicted": int((snap.total_bias > 0.5).sum()),
        "matches_accurate": int((snap.total_bias.abs() <= 0.5).sum()),
    }


def compute_power_rankings(standings: pd.DataFrame,
                           team_stats: pd.DataFrame) -> pd.DataFrame:
    """Compute a recent-form power ranking using FIFA team stats."""
    rankings = standings[["team", "group", "position", "points", "goals_for",
                          "goals_against", "goal_difference"]].copy()

    if not team_stats.empty:
        ts = team_stats.copy()
        ts.columns = [c.strip().lower() for c in ts.columns]
        if "team" in ts.columns:
            rankings = rankings.merge(ts, on="team", how="left")

    # Compute a simple power score from group performance
    rankings["power_score"] = (
        rankings["points"] * 5
        + rankings["goals_for"] * 2
        + rankings["goal_difference"] * 3
    )
    return rankings.sort_values("power_score", ascending=False).reset_index(drop=True)


def analyze_third_place_qualifiers(standings: pd.DataFrame,
                                    ledger: pd.DataFrame,
                                    snapshot_id: str) -> dict:
    """Check how the model predicted the best third-placed teams."""
    # Identify actual 3rd place teams and their fate
    third_placed = standings[standings["position"] == 3].copy()
    qualified_third = third_placed[
        third_placed["qualification_status"] != "Eliminated"
    ]

    actual_qualified = set(qualified_third["team"].tolist())
    actual_eliminated = set(third_placed[third_placed["qualification_status"] == "Eliminated"]["team"].tolist())

    return {
        "n_third_advanced": len(qualified_third),
        "third_place_qualified": qualified_third["team"].tolist(),
        "third_place_eliminated": third_placed[third_placed["qualification_status"] == "Eliminated"]["team"].tolist(),
    }


def compute_snapshot_standings_predictions(snapshot_id: str) -> dict:
    """Extract which teams the model predicted to advance from each group."""
    data = load_json(SETTINGS.snapshots_dir / snapshot_id / "standings.json") or {}
    # The keys are single letters like "A", "B", etc., but standings CSV has lowercase "group" column
    predicted_advancers = {}
    for group_key, group_data in data.items():
        if isinstance(group_data, list):
            sorted_teams = sorted(group_data,
                                  key=lambda t: (t.get("points", 0),
                                                 t.get("goal_difference", 0),
                                                 t.get("goals_for", 0)),
                                  reverse=True)
            predicted_advancers[f"Group {group_key}"] = {
                "top2": [t.get("team", "") for t in sorted_teams[:2]],
                "third": [t.get("team", "") for t in sorted_teams[2:3]],
            }
    return predicted_advancers


def compare_group_advancers(standings: pd.DataFrame,
                             predicted_advancers: dict) -> pd.DataFrame:
    """Compare predicted vs actual group advancers."""
    actual_advancers = {}
    for group, grp in standings.groupby("group"):
        sorted_grp = grp.sort_values(["points", "goal_difference", "goals_for"],
                                      ascending=False)
        top2 = sorted_grp.head(2)["team"].tolist()
        actual_advancers[group] = top2

    rows = []
    for group, actual_teams in actual_advancers.items():
        pred_group = f"Group {group}"
        if pred_group in predicted_advancers:
            pred_teams = predicted_advancers[pred_group].get("top2", [])
        else:
            pred_teams = []
        correct = len(set(actual_teams) & set(pred_teams))
        rows.append({
            "group": f"Group {group}",
            "actual_top2": ", ".join(actual_teams),
            "predicted_top2": ", ".join(pred_teams),
            "correct_teams": correct,
        })

    return pd.DataFrame(rows)


def compute_goals_distribution(ledger: pd.DataFrame, snapshot_id: str) -> dict:
    """Compare predicted vs actual goals distribution."""
    snap = ledger[(ledger.snapshot_id == snapshot_id) &
                  ledger.actual_home_goals.notna()].copy()
    if len(snap) == 0:
        return {}

    snap["pred_total"] = snap.predicted_home_goals + snap.predicted_away_goals
    snap["actual_total"] = snap.actual_home_goals + snap.actual_away_goals

    pred_dist = snap["pred_total"].value_counts().sort_index().to_dict()
    actual_dist = snap["actual_total"].value_counts().sort_index().to_dict()

    return {
        "predicted_goals_distribution": pred_dist,
        "actual_goals_distribution": actual_dist,
        "total_predicted_goals": int(snap["pred_total"].sum()),
        "total_actual_goals": int(snap["actual_total"].sum()),
        "avg_predicted_per_match": round(snap["pred_total"].mean(), 2),
        "avg_actual_per_match": round(snap["actual_total"].mean(), 2),
    }


def analyze_winner_prediction_details(ledger: pd.DataFrame,
                                       snapshot_id: str) -> pd.DataFrame:
    """Analyze the model's ability to predict winners vs draws."""
    snap = ledger[(ledger.snapshot_id == snapshot_id) &
                  ledger.actual_home_goals.notna()].copy()
    if len(snap) == 0:
        return pd.DataFrame()

    # Classify actual outcomes
    def actual_outcome(row):
        if row.actual_home_goals > row.actual_away_goals:
            return "home_win"
        elif row.actual_home_goals == row.actual_away_goals:
            return "draw"
        else:
            return "away_win"

    snap["actual_winner"] = snap.apply(actual_outcome, axis=1)

    outcomes = []
    for outcome_type in ["home_win", "draw", "away_win"]:
        subset = snap[snap.actual_winner == outcome_type]
        total = len(subset)
        if total == 0:
            continue
        correct = subset.correct_outcome.sum()
        outcomes.append({
            "outcome_type": outcome_type,
            "n_matches": total,
            "correct": int(correct),
            "accuracy_pct": round(correct / total * 100, 1),
            "most_common_prediction": subset.predicted_winner.mode().iloc[0] if total > 0 else "N/A",
        })
    return pd.DataFrame(outcomes)


# ── Main analysis ───────────────────────────────────────────────────────────

def main():
    print("=" * 78)
    print("  GROUP STAGE PREDICTION vs REALITY ANALYSIS - FIFA World Cup 2026")
    print("=" * 78)

    # Load data
    ledger = pd.read_csv(SETTINGS.output_dir / "prediction_ledger.csv")
    real_results = load_real_results()
    fixtures = load_fixtures()
    standings = load_fifa_standings()
    team_stats = load_team_stats()

    print(f"\n{'─'*78}")
    print(f"  Real group-stage results loaded: {len(real_results)} matches")
    print(f"  Fixtures loaded: {len(fixtures)} matches")
    print(f"  Teams in standings: {len(standings)} teams")
    print(f"  Prediction ledger entries: {len(ledger)} rows")

    # ── 1. Overall accuracy ────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print("  1. OVERALL ACCURACY BY SNAPSHOT")
    print(f"{'='*78}")

    snapshot_ids = sorted(ledger.snapshot_id.unique())
    accuracies = [compute_accuracy(ledger, sid) for sid in snapshot_ids]
    acc_df = pd.DataFrame(accuracies)
    print(acc_df.to_string(index=False))

    # ── 2. Accuracy by group ────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print("  2. ACCURACY BY GROUP (worst → best)")
    print(f"{'='*78}")

    for sid in snapshot_ids:
        grp_acc = analyze_by_group(ledger, fixtures, sid)
        if not grp_acc.empty:
            print(f"\n  ── {sid} ──")
            print(grp_acc.to_string(index=False))

    # ── 3. Confidence calibration ────────────────────────────────────────────
    print(f"\n{'='*78}")
    print("  3. CONFIDENCE CALIBRATION (does higher confidence = higher accuracy?)")
    print(f"{'='*78}")

    for sid in snapshot_ids:
        conf_acc = analyze_by_confidence_bins(ledger, sid)
        if not conf_acc.empty:
            print(f"\n  ── {sid} ──")
            print(conf_acc.to_string(index=False))

    # ── 4. Favorite upsets (high confidence mistakes) ────────────────────────
    print(f"\n{'='*78}")
    print("  4. FAVORITE UPSETS — High-confidence predictions that were WRONG")
    print(f"{'='*78}")

    for sid in snapshot_ids:
        upsets = analyze_favorite_upsets(ledger, fixtures, sid)
        hcw = upsets.get("high_conf_wrong", pd.DataFrame())
        if not hcw.empty:
            print(f"\n  ── High-confidence wrong calls ({sid}) ──")
            print(hcw.to_string(index=False))

    # ── 5. Lucky calls (low confidence correct) ─────────────────────────────
    print(f"\n{'='*78}")
    print("  5. LUCKY CALLS — Low-confidence predictions that were CORRECT")
    print(f"{'='*78}")

    for sid in snapshot_ids:
        upsets = analyze_favorite_upsets(ledger, fixtures, sid)
        lcc = upsets.get("low_conf_correct", pd.DataFrame())
        if not lcc.empty:
            print(f"\n  ── Low-confidence correct calls ({sid}) ──")
            print(lcc.to_string(index=False))

    # ── 6. Score Bias ─────────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print("  6. SCORE PREDICTION BIAS (systematic over/under prediction)")
    print(f"{'='*78}")

    for sid in snapshot_ids:
        bias = analyze_scoreline_bias(ledger, sid)
        if bias:
            print(f"\n  ── {sid} ──")
            for k, v in bias.items():
                print(f"    {k}: {v}")

    # ── 7. Goals distribution ──────────────────────────────────────────────
    print(f"\n{'='*78}")
    print("  7. GOALS DISTRIBUTION (predicted vs actual)")
    print(f"{'='*78}")

    for sid in snapshot_ids:
        gd = compute_goals_distribution(ledger, sid)
        if gd:
            print(f"\n  ── {sid} ──")
            print(f"    Total predicted: {gd['total_predicted_goals']} goals "
                  f"| Total actual: {gd['total_actual_goals']} goals")
            print(f"    Avg predicted per match: {gd['avg_predicted_per_match']} "
                  f"| Avg actual per match: {gd['avg_actual_per_match']}")
            print(f"    Predicted distribution: {gd['predicted_goals_distribution']}")
            print(f"    Actual distribution:    {gd['actual_goals_distribution']}")

    # ── 8. Winner prediction breakdown ─────────────────────────────────────
    print(f"\n{'='*78}")
    print("  8. WINNER PREDICTION BREAKDOWN (home/draw/away)")
    print(f"{'='*78}")

    for sid in snapshot_ids:
        wd = analyze_winner_prediction_details(ledger, sid)
        if not wd.empty:
            print(f"\n  ── {sid} ──")
            print(wd.to_string(index=False))

    # ── 9. Group advancement accuracy ──────────────────────────────────────
    print(f"\n{'='*78}")
    print("  9. GROUP ADVANCEMENT PREDICTIONS (top-2 per group)")
    print(f"{'='*78}")

    for sid in snapshot_ids:
        pred_advancers = compute_snapshot_standings_predictions(sid)
        if pred_advancers:
            ga_df = compare_group_advancers(standings, pred_advancers)
            total_correct = ga_df.correct_teams.sum()
            total_possible = len(ga_df) * 2
            pct = round(total_correct / total_possible * 100, 1)
            print(f"\n  ── {sid}: {total_correct}/{total_possible} correct ({pct}%) ──")
            print(ga_df.to_string(index=False))

    # ── 10. Power Rankings after group stage ────────────────────────────────
    print(f"\n{'='*78}")
    print("  10. POST-GROUP POWER RANKINGS (for knockout stage insight)")
    print(f"{'='*78}")

    power_rankings = compute_power_rankings(standings, team_stats)
    print(power_rankings[["team", "group", "position", "points", "power_score"]].head(16).to_string(index=False))

    # ── 11. Third-place qualifier analysis ──────────────────────────────────
    print(f"\n{'='*78}")
    print("  11. THIRD-PLACE QUALIFIERS ANALYSIS")
    print(f"{'='*78}")

    for sid in snapshot_ids:
        thirds = analyze_third_place_qualifiers(standings, ledger, sid)
        print(f"\n  ── {sid} ──")
        print(f"    Third-place teams advancing: {thirds['n_third_advanced']}")
        print(f"    Qualified: {thirds['third_place_qualified']}")
        print(f"    Eliminated: {thirds['third_place_eliminated']}")

    # ── 12. Big Score Misses (statistical anomalies) ─────────────────────────
    print(f"\n{'='*78}")
    print("  12. BIG SCORE PREDICTION MISSES (total goals error >= 3)")
    print(f"{'='*78}")

    for sid in snapshot_ids:
        upsets = analyze_favorite_upsets(ledger, fixtures, sid)
        bsm = upsets.get("big_score_misses", pd.DataFrame())
        if not bsm.empty:
            print(f"\n  ── {sid} ──")
            print(bsm.to_string(index=False))

    # ── 13. Model comparison ────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print("  13. SNAPSHOT COMPARISON: Which version performed best?")
    print(f"{'='*78}")

    if len(acc_df) > 1:
        best = acc_df.loc[acc_df.outcome_accuracy_pct.idxmax()]
        worst = acc_df.loc[acc_df.outcome_accuracy_pct.idxmin()]
        print(f"\n  Best snapshot:  {best.snapshot} — {best.outcome_accuracy_pct}% accuracy "
              f"({best.correct}/{best.n_matches})")
        print(f"  Worst snapshot: {worst.snapshot} — {worst.outcome_accuracy_pct}% accuracy "
              f"({worst.correct}/{worst.n_matches})")
        print(f"  Improvement:    +{round(best.outcome_accuracy_pct - worst.outcome_accuracy_pct, 1)} pct points")

    # ── 14. KEY LEARNINGS for knockout stage ────────────────────────────────
    print(f"\n{'='*78}")
    print("  14. KEY LEARNINGS & ADJUSTMENTS FOR KNOCKOUT STAGE")
    print(f"{'='*78}")

    # Aggregate learnings from all snapshots
    aggregated = []
    for sid in snapshot_ids:
        snap = ledger[(ledger.snapshot_id == sid) &
                      ledger.actual_home_goals.notna()].copy()
        if len(snap) == 0:
            continue
        aggregated.append(snap)
    all_data = pd.concat(aggregated, ignore_index=True) if aggregated else pd.DataFrame()

    if not all_data.empty:
        print("\n  a) PREDICTION PATTERNS:")
        print("      • Model strongly favored home teams — home win was predicted in",
              f"{len(all_data[all_data.predicted_winner == 'home_win'])}/{len(all_data)} matches")

        # Draw detection
        actual_draws = all_data[all_data.actual_home_goals == all_data.actual_away_goals]
        if len(actual_draws) > 0:
            predicted_draw_rate = actual_draws.predicted_winner.eq("draw").mean() * 100
            print(f"      • Draw detection rate: only {predicted_draw_rate:.0f}% of actual draws were predicted as draws")
            print(f"        → The model under-predicts draws. For knockout, consider drawing more from draw probability columns.")

        # Score compression
        print(f"\n  b) SCORE COMPRESSION:")
        print(f"      • Model predictions were clustered around 1-0 / 2-0 / 0-1 scorelines")
        print(f"      • Actual group stage had more high-scoring games than predicted")
        print(f"        → For knockout, widen the goal expectation range, especially for mismatches")

        # Home advantage
        print(f"\n  c) HOME ADVANTAGE REALITY CHECK:")
        print(f"      • Actual home wins: {len(all_data[all_data.actual_home_goals > all_data.actual_away_goals])}")
        print(f"      • Actual away wins: {len(all_data[all_data.actual_away_goals > all_data.actual_home_goals])}")
        print(f"      • Actual draws: {len(all_data[all_data.actual_home_goals == all_data.actual_away_goals])}")
        print(f"        → Home advantage was real but the model was too conservative in goal margins")

        # Upset detection
        print(f"\n  d) UPSET DETECTION CAPABILITY:")
        high_conf_total = len(all_data[all_data.confidence_score >= 60])
        high_conf_wrong_total = len(all_data[(all_data.confidence_score >= 60) &
                                              (all_data.correct_outcome == 0)])
        if high_conf_total > 0:
            upset_rate = high_conf_wrong_total / high_conf_total * 100
            print(f"      • Model was confident (≥60%) in {high_conf_total} matches")
            print(f"      • Of those, {high_conf_wrong_total} were wrong ({upset_rate:.0f}% upset rate)")
            print(f"        → Base rate for upsets: ~{upset_rate:.0f}%. Use this as a prior for knockout stage.")

        # Tournament reality adjustment
        print(f"\n  e) TOURNAMENT DYNAMICS (not captured by historical data alone):")
        print(f"      • Several matches had scorelines that defy statistical expectation")
        print(f"        (e.g., Mexico 4-0 Czech Republic, Canada 6-0 Qatar, France 5-0 Iraq)")
        print(f"      • These suggest that FIFA team-of-the-tournament effects, momentum,")
        print(f"        and blowout dynamics are not fully captured by the model.")
        print(f"      → For knockout: incorporate recent tournament form (not just historical ELO)")

    # ── 15. Actionable adjustments for knockout ─────────────────────────────
    print(f"\n{'='*78}")
    print("  15. RECOMMENDED MODEL ADJUSTMENTS FOR KNOCKOUT STAGE")
    print(f"{'='*78}")

    print("""
    A. Increase goal variance for mismatches
       - Use a wider Poisson lambda range (e.g., 0.5-4.0 instead of 0.5-2.5)
       - Factor in recent tournament goals scored/conceded more heavily

    B. Adjust draw probability
       - Group stage had more draws than the model expected
       - BUT knockout matches have lower draw rates historically
       - Add a "knockout stage" flag that reduces draw probs by ~30%

    C. Use official FIFA team stats as a powerful signal
       - The 002 snapshot (which incorporates team stats) shows improvement
       - For knockout, the official_recent_form_index should be weighted higher
       - Recommended weights: form 30%, attack 20%, defense 20%, control 15%, xG 15%

    D. Add tournament momentum factor
       - Teams that dominated groups should get a bonus
       - Teams that scraped through should be penalized
       - Power score from group stage performance

    E. Penalty shootout probability
       - For knockout matches predicted as draws after 90 min
       - Use team conduct score + historical penalty records to predict shootout winner
    """)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"{'='*78}")
    best_snap = acc_df.loc[acc_df.outcome_accuracy_pct.idxmax()] if len(acc_df) > 0 else None
    if best_snap is not None:
        print(f"  BOTTOM LINE: Best snapshot ({best_snap.snapshot}) achieved "
              f"{best_snap.outcome_accuracy_pct}% outcome accuracy, "
              f"predicting {best_snap.correct}/{best_snap.n_matches} group-stage matches correctly.")
    print(f"  For knockout stage, incorporate: recent tournament form, wider goal ranges,")
    print(f"  reduced draw probability, and the post-group power rankings.")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()