from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import (
    FINAL_POLICY_SIMULATION_REPORT_PATH,
    FINAL_POLICY_SIMULATION_SUMMARY_PATH,
    FINAL_POLICY_SIMULATION_TABLE_PATH,
    FINAL_SCORED_CSV_PATH,
)
from reporting.evaluation_utils import load_scored_splits, safe_float, safe_int, write_csv


SIMULATION_COLUMNS = [
    "calendar_date",
    "building_id",
    "target",
    "model_probability",
    "cumulative_complaints_prior",
    "rolling_7d_complaints",
    "open_linked_violation_count",
    "complaint_count",
    "heat_sensor_active_flag",
    "cre_vulnerability_index",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate daily inspection policies on held-out scored outputs.")
    parser.add_argument("--input", default=str(FINAL_SCORED_CSV_PATH), help="Scored CSV with model outputs.")
    parser.add_argument(
        "--daily-output",
        default=str(FINAL_POLICY_SIMULATION_TABLE_PATH),
        help="CSV output path for daily policy simulation results.",
    )
    parser.add_argument(
        "--summary-output",
        default=str(FINAL_POLICY_SIMULATION_SUMMARY_PATH),
        help="CSV output path for aggregated policy summaries.",
    )
    parser.add_argument(
        "--report-output",
        default=str(FINAL_POLICY_SIMULATION_REPORT_PATH),
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--capacities",
        default="10,25,50,100",
        help="Comma-separated daily inspection capacities to simulate.",
    )
    return parser.parse_args()


def order_policy(group: pd.DataFrame, policy: str) -> pd.DataFrame:
    if policy == "model_probability":
        return group.sort_values(["model_probability", "building_id"], ascending=[False, True])
    if policy == "equity_weighted":
        ordered = group.copy()
        ordered["policy_score"] = ordered["model_probability"] * (1.0 + ordered["cre_vulnerability_index"])
        return ordered.sort_values(["policy_score", "building_id"], ascending=[False, True])
    if policy == "history_baseline":
        return group.sort_values(
            [
                "cumulative_complaints_prior",
                "rolling_7d_complaints",
                "open_linked_violation_count",
                "complaint_count",
                "cre_vulnerability_index",
                "building_id",
            ],
            ascending=[False, False, False, False, False, True],
        )
    raise ValueError(f"Unsupported policy: {policy}")


def build_daily_rows(df: pd.DataFrame, capacities: list[int]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    policies = ["model_probability", "equity_weighted", "history_baseline"]
    for calendar_date, group in df.groupby("calendar_date"):
        actual_positive_rate = float(group["target"].mean())
        total_positives = int(group["target"].sum())
        ordered_by_policy = {policy: order_policy(group, policy).reset_index(drop=True) for policy in policies}
        for capacity in capacities:
            random_expected_hits = actual_positive_rate * capacity
            random_expected_recall = float(random_expected_hits / total_positives) if total_positives else 0.0
            rows.append(
                {
                    "calendar_date": calendar_date,
                    "policy": "random_expectation",
                    "capacity": capacity,
                    "rows_available": int(len(group)),
                    "actual_positive_rate": round(actual_positive_rate, 6),
                    "total_positives": total_positives,
                    "hits": round(random_expected_hits, 4),
                    "precision": round(actual_positive_rate, 6),
                    "recall": round(random_expected_recall, 6),
                    "lift": 1.0 if actual_positive_rate else 0.0,
                    "avg_cre_vulnerability": round(float(group["cre_vulnerability_index"].mean()), 6),
                    "avg_open_violations": round(float(group["open_linked_violation_count"].mean()), 6),
                }
            )
            for policy in policies:
                ordered = ordered_by_policy[policy].head(capacity)
                hits = int(ordered["target"].sum())
                precision = float(ordered["target"].mean()) if len(ordered) else 0.0
                recall = float(hits / total_positives) if total_positives else 0.0
                lift = float(precision / actual_positive_rate) if actual_positive_rate else 0.0
                rows.append(
                    {
                        "calendar_date": calendar_date,
                        "policy": policy,
                        "capacity": capacity,
                        "rows_available": int(len(group)),
                        "actual_positive_rate": round(actual_positive_rate, 6),
                        "total_positives": total_positives,
                        "hits": hits,
                        "precision": round(precision, 6),
                        "recall": round(recall, 6),
                        "lift": round(lift, 6),
                        "avg_cre_vulnerability": round(float(ordered["cre_vulnerability_index"].mean()), 6),
                        "avg_open_violations": round(float(ordered["open_linked_violation_count"].mean()), 6),
                    }
                )
    return rows


def summarize_daily_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    if not rows:
        return []
    df = pd.DataFrame(rows)
    summary_rows: list[dict[str, object]] = []
    for (policy, capacity), group in df.groupby(["policy", "capacity"]):
        summary_rows.append(
            {
                "policy": policy,
                "capacity": int(capacity),
                "days": int(len(group)),
                "mean_hits": round(float(group["hits"].mean()), 4),
                "mean_precision": round(float(group["precision"].mean()), 4),
                "mean_recall": round(float(group["recall"].mean()), 4),
                "mean_lift": round(float(group["lift"].mean()), 4),
                "mean_avg_cre_vulnerability": round(float(group["avg_cre_vulnerability"].mean()), 4),
                "mean_avg_open_violations": round(float(group["avg_open_violations"].mean()), 4),
            }
        )
    summary = pd.DataFrame(summary_rows)
    random_hits = summary[summary["policy"] == "random_expectation"][["capacity", "mean_hits"]].rename(
        columns={"mean_hits": "random_mean_hits"}
    )
    history_hits = summary[summary["policy"] == "history_baseline"][["capacity", "mean_hits"]].rename(
        columns={"mean_hits": "history_mean_hits"}
    )
    summary = summary.merge(random_hits, on="capacity", how="left")
    summary = summary.merge(history_hits, on="capacity", how="left")
    summary["delta_hits_vs_random"] = (summary["mean_hits"] - summary["random_mean_hits"]).round(4)
    summary["delta_hits_vs_history"] = (summary["mean_hits"] - summary["history_mean_hits"]).round(4)
    return summary.sort_values(["capacity", "policy"]).to_dict(orient="records")


def write_report(path: Path, summary_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Inspection Policy Simulation",
        "",
        "This report compares daily inspection-capacity policies on the held-out test period.",
        "Policies:",
        "- `model_probability`: calibrated logistic ranking",
        "- `equity_weighted`: calibrated risk multiplied by `(1 + CRE vulnerability)`",
        "- `history_baseline`: complaint-history and violation-first heuristic",
        "- `random_expectation`: expected value under random selection",
        "",
    ]

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        for capacity in sorted(summary_df["capacity"].unique()):
            bucket = summary_df[summary_df["capacity"] == capacity].copy()
            bucket = bucket.sort_values("mean_hits", ascending=False)
            best = bucket.iloc[0]
            logistic = bucket[bucket["policy"] == "model_probability"].iloc[0]
            equity = bucket[bucket["policy"] == "equity_weighted"].iloc[0]
            history = bucket[bucket["policy"] == "history_baseline"].iloc[0]
            random_row = bucket[bucket["policy"] == "random_expectation"].iloc[0]

            lines.extend(
                [
                    f"## Capacity {capacity}",
                    f"- Best mean hits/day: `{best['policy']}` with `{best['mean_hits']}`",
                    f"- Calibrated logistic mean hits/day: `{logistic['mean_hits']}`",
                    f"- Equity-weighted mean hits/day: `{equity['mean_hits']}`",
                    f"- History baseline mean hits/day: `{history['mean_hits']}`",
                    f"- Random expected hits/day: `{random_row['mean_hits']}`",
                    f"- Logistic delta vs random: `+{logistic['delta_hits_vs_random']}` hits/day",
                    f"- Logistic delta vs history: `{logistic['delta_hits_vs_history']}` hits/day",
                    f"- Equity list mean CRE vulnerability: `{equity['mean_avg_cre_vulnerability']}`",
                    f"- Logistic mean lift: `{logistic['mean_lift']}` | Equity mean lift: `{equity['mean_lift']}`",
                    "",
                ]
            )

        lines.extend(
            [
                "## Interpretation",
                "- This simulation translates ranking metrics into a field-capacity question: how many true positive buildings are found per day at a fixed inspection budget?",
                "- If the equity-weighted list finds nearly as many positives as the pure calibrated ranking while concentrating higher vulnerability scores, the public-sector tradeoff becomes easier to defend.",
            ]
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    capacities = [int(item.strip()) for item in args.capacities.split(",") if item.strip()]
    scored = load_scored_splits(Path(args.input), SIMULATION_COLUMNS, {"test"})
    if scored.empty:
        raise ValueError("No test rows were found in the scored CSV.")

    scored["calendar_date"] = pd.to_datetime(scored["calendar_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    numeric_columns = [
        "target",
        "model_probability",
        "cumulative_complaints_prior",
        "rolling_7d_complaints",
        "open_linked_violation_count",
        "complaint_count",
        "heat_sensor_active_flag",
        "cre_vulnerability_index",
    ]
    for column in numeric_columns:
        scored[column] = pd.to_numeric(scored[column], errors="coerce").fillna(0)

    daily_rows = build_daily_rows(scored, capacities)
    summary_rows = summarize_daily_rows(daily_rows)

    write_csv(Path(args.daily_output), daily_rows)
    write_csv(Path(args.summary_output), summary_rows)
    write_report(Path(args.report_output), summary_rows)

    print(f"wrote daily simulation rows to {args.daily_output}", flush=True)
    print(f"wrote summary rows to {args.summary_output}", flush=True)
    print(f"wrote report to {args.report_output}", flush=True)


if __name__ == "__main__":
    main()
