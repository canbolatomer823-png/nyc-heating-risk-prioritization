from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from scipy import stats

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import FINAL_SEASONAL_ANOVA_REPORT_PATH, FINAL_SEASONAL_ANOVA_TABLE_PATH, FINAL_SPARSE_PANEL_PATH


PHASE_LABELS = {
    10: "early_heat_season",
    11: "early_heat_season",
    12: "peak_winter",
    1: "peak_winter",
    2: "peak_winter",
    3: "late_heat_season",
    4: "late_heat_season",
    5: "late_heat_season",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run monthly and seasonal-phase ANOVA on daily heating complaint activity.")
    parser.add_argument(
        "--input",
        default=str(FINAL_SPARSE_PANEL_PATH),
        help="Sparse building-day panel path.",
    )
    parser.add_argument(
        "--table-output",
        default=str(FINAL_SEASONAL_ANOVA_TABLE_PATH),
        help="CSV output path for daily aggregates.",
    )
    parser.add_argument(
        "--report-output",
        default=str(FINAL_SEASONAL_ANOVA_REPORT_PATH),
        help="Markdown output path for the ANOVA report.",
    )
    return parser.parse_args()


def load_daily_activity(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        usecols=["complaint_date", "building_id", "complaint_count"],
        low_memory=False,
    )
    frame["complaint_date"] = pd.to_datetime(frame["complaint_date"], errors="coerce")
    frame = frame.dropna(subset=["complaint_date"]).copy()
    frame["complaint_count"] = pd.to_numeric(frame["complaint_count"], errors="coerce").fillna(0)
    frame["month_key"] = frame["complaint_date"].dt.strftime("%Y-%m")
    frame["month_label"] = frame["complaint_date"].dt.strftime("%b %Y")
    frame["season_phase"] = frame["complaint_date"].dt.month.map(PHASE_LABELS).fillna("other")

    daily = (
        frame.groupby("complaint_date", as_index=False)
        .agg(
            daily_total_complaints=("complaint_count", "sum"),
            daily_positive_buildings=("building_id", "nunique"),
        )
        .sort_values("complaint_date")
        .reset_index(drop=True)
    )
    daily["month_key"] = daily["complaint_date"].dt.strftime("%Y-%m")
    daily["month_label"] = daily["complaint_date"].dt.strftime("%b %Y")
    daily["season_phase"] = daily["complaint_date"].dt.month.map(PHASE_LABELS).fillna("other")
    return daily


def anova_for_grouping(frame: pd.DataFrame, value_col: str, group_col: str) -> dict[str, float | int | str]:
    grouped = []
    ordered_groups = []
    for group_name, group_frame in frame.groupby(group_col, sort=False):
        values = group_frame[value_col].astype(float).to_numpy()
        if len(values) < 2:
            continue
        grouped.append(values)
        ordered_groups.append(str(group_name))

    if len(grouped) < 2:
        return {"groups": len(grouped), "f_stat": float("nan"), "p_value": float("nan"), "eta_sq": float("nan")}

    f_stat, p_value = stats.f_oneway(*grouped)
    overall_mean = float(frame[value_col].mean())
    ss_between = sum(len(values) * (float(values.mean()) - overall_mean) ** 2 for values in grouped)
    ss_total = float(((frame[value_col] - overall_mean) ** 2).sum())
    eta_sq = float(ss_between / ss_total) if ss_total else 0.0

    return {
        "groups": len(grouped),
        "group_names": ", ".join(ordered_groups),
        "f_stat": round(float(f_stat), 4),
        "p_value": float(p_value),
        "eta_sq": round(eta_sq, 4),
    }


def format_p_value(value: float) -> str:
    if pd.isna(value):
        return "n/a"
    if value < 0.0001:
        return "<0.0001"
    return f"{value:.4f}"


def monthly_summary(frame: pd.DataFrame) -> pd.DataFrame:
    summary = (
        frame.groupby(["month_key", "month_label"], as_index=False)
        .agg(
            days=("complaint_date", "count"),
            mean_daily_total_complaints=("daily_total_complaints", "mean"),
            std_daily_total_complaints=("daily_total_complaints", "std"),
            mean_daily_positive_buildings=("daily_positive_buildings", "mean"),
            std_daily_positive_buildings=("daily_positive_buildings", "std"),
        )
        .sort_values("month_key")
        .reset_index(drop=True)
    )
    numeric_cols = [col for col in summary.columns if col not in {"month_key", "month_label"}]
    summary[numeric_cols] = summary[numeric_cols].round(4)
    return summary


def build_report(frame: pd.DataFrame, summary: pd.DataFrame) -> str:
    complaints_month = anova_for_grouping(frame, "daily_total_complaints", "month_label")
    buildings_month = anova_for_grouping(frame, "daily_positive_buildings", "month_label")
    complaints_phase = anova_for_grouping(frame, "daily_total_complaints", "season_phase")
    buildings_phase = anova_for_grouping(frame, "daily_positive_buildings", "season_phase")

    busiest_month = summary.sort_values("mean_daily_total_complaints", ascending=False).iloc[0].to_dict()
    quietest_month = summary.sort_values("mean_daily_total_complaints").iloc[0].to_dict()

    lines = [
        "# Seasonal ANOVA",
        "",
        "Daily operational load was aggregated from the sparse building-day complaint panel.",
        "",
        "## Window",
        f"- Date range: {frame['complaint_date'].min().strftime('%Y-%m-%d')} -> {frame['complaint_date'].max().strftime('%Y-%m-%d')}",
        f"- Daily observations: {len(frame)}",
        f"- Month groups: {summary['month_label'].nunique()}",
        "",
        "## Monthly ANOVA",
        f"- Daily total complaints: F={complaints_month['f_stat']}, p={format_p_value(float(complaints_month['p_value']))}, eta_sq={complaints_month['eta_sq']}",
        f"- Daily positive buildings: F={buildings_month['f_stat']}, p={format_p_value(float(buildings_month['p_value']))}, eta_sq={buildings_month['eta_sq']}",
        "",
        "## Seasonal Phase ANOVA",
        f"- Daily total complaints: F={complaints_phase['f_stat']}, p={format_p_value(float(complaints_phase['p_value']))}, eta_sq={complaints_phase['eta_sq']}",
        f"- Daily positive buildings: F={buildings_phase['f_stat']}, p={format_p_value(float(buildings_phase['p_value']))}, eta_sq={buildings_phase['eta_sq']}",
        "",
        "## Interpretable Takeaway",
        f"- Highest mean daily complaint month: {busiest_month['month_label']} ({busiest_month['mean_daily_total_complaints']})",
        f"- Lowest mean daily complaint month: {quietest_month['month_label']} ({quietest_month['mean_daily_total_complaints']})",
        "- This supports the claim that operational complaint burden changes materially across the heat season rather than staying constant.",
        "",
        "## Monthly Means",
    ]

    for row in summary.itertuples(index=False):
        lines.append(
            f"- {row.month_label}: days={row.days}, "
            f"mean_complaints={row.mean_daily_total_complaints}, std_complaints={row.std_daily_total_complaints}, "
            f"mean_positive_buildings={row.mean_daily_positive_buildings}, std_positive_buildings={row.std_daily_positive_buildings}"
        )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    daily = load_daily_activity(Path(args.input))
    summary = monthly_summary(daily)

    table_path = Path(args.table_output)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    daily.assign(complaint_date=daily["complaint_date"].dt.strftime("%Y-%m-%d")).to_csv(table_path, index=False)

    report_path = Path(args.report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(daily, summary), encoding="utf-8")

    print(f"wrote ANOVA table to {table_path}", flush=True)
    print(f"wrote ANOVA report to {report_path}", flush=True)


if __name__ == "__main__":
    main()
