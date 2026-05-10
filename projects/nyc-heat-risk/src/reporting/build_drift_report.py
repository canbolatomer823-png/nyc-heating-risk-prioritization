from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import FINAL_DRIFT_REPORT_PATH, FINAL_DRIFT_TABLE_PATH, FINAL_SCORED_CSV_PATH
from reporting.evaluation_utils import write_csv


NUMERIC_FEATURES = [
    "weather_heating_degree_c",
    "weather_temp_drop_c",
    "rolling_7d_complaints",
    "cumulative_complaints_prior",
    "open_linked_violation_count",
    "cre_vulnerability_index",
    "unit_count_proxy",
]

CATEGORICAL_FEATURES = ["borough", "management_program"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a train-vs-test drift report from the scored benchmark output.")
    parser.add_argument("--input", default=str(FINAL_SCORED_CSV_PATH), help="Scored CSV input path.")
    parser.add_argument(
        "--metrics-output",
        default=str(FINAL_DRIFT_TABLE_PATH),
        help="CSV output path for drift metrics.",
    )
    parser.add_argument(
        "--report-output",
        default=str(FINAL_DRIFT_REPORT_PATH),
        help="Markdown output path.",
    )
    parser.add_argument("--max-sample-rows", type=int, default=250_000, help="Maximum sampled rows per split.")
    parser.add_argument("--random-state", type=int, default=42, help="Sampling random seed.")
    return parser.parse_args()


def downsample(df: pd.DataFrame, max_rows: int, random_state: int) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df
    return df.sample(n=max_rows, random_state=random_state).reset_index(drop=True)


def collect_split_samples(path: Path, max_rows: int, random_state: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    usecols = ["data_split", *NUMERIC_FEATURES, *CATEGORICAL_FEATURES]
    train = pd.DataFrame(columns=usecols)
    test = pd.DataFrame(columns=usecols)
    for chunk_index, chunk in enumerate(
        pd.read_csv(
            path,
            usecols=lambda column: column in set(usecols),
            chunksize=250_000,
            low_memory=False,
        )
    ):
        train_chunk = chunk[chunk["data_split"] == "train"].copy()
        test_chunk = chunk[chunk["data_split"] == "test"].copy()
        if not train_chunk.empty:
            train = train_chunk.reset_index(drop=True) if train.empty else pd.concat([train, train_chunk], ignore_index=True)
            if len(train) > max_rows * 2:
                train = downsample(train, max_rows, random_state + chunk_index)
        if not test_chunk.empty:
            test = test_chunk.reset_index(drop=True) if test.empty else pd.concat([test, test_chunk], ignore_index=True)
            if len(test) > max_rows * 2:
                test = downsample(test, max_rows, random_state + 10_000 + chunk_index)
    train = downsample(train, max_rows, random_state)
    test = downsample(test, max_rows, random_state + 1)
    return train, test


def population_stability_index(train: pd.Series, test: pd.Series, bins: int = 10) -> float:
    train_clean = train.dropna().to_numpy(dtype=float)
    test_clean = test.dropna().to_numpy(dtype=float)
    if train_clean.size == 0 or test_clean.size == 0:
        return 0.0
    quantiles = np.unique(np.quantile(train_clean, np.linspace(0, 1, bins + 1)))
    if len(quantiles) < 3:
        return 0.0
    train_counts, _ = np.histogram(train_clean, bins=quantiles)
    test_counts, _ = np.histogram(test_clean, bins=quantiles)
    train_pct = np.clip(train_counts / max(train_counts.sum(), 1), 1e-6, None)
    test_pct = np.clip(test_counts / max(test_counts.sum(), 1), 1e-6, None)
    return float(np.sum((test_pct - train_pct) * np.log(test_pct / train_pct)))


def total_variation_distance(train: pd.Series, test: pd.Series) -> tuple[float, str]:
    train_dist = train.fillna("UNKNOWN").astype(str).value_counts(normalize=True)
    test_dist = test.fillna("UNKNOWN").astype(str).value_counts(normalize=True)
    categories = sorted(set(train_dist.index) | set(test_dist.index))
    max_gap_label = "n/a"
    max_gap = -1.0
    total = 0.0
    for category in categories:
        diff = abs(float(train_dist.get(category, 0.0)) - float(test_dist.get(category, 0.0)))
        total += diff
        if diff > max_gap:
            max_gap = diff
            max_gap_label = category
    return float(total / 2.0), max_gap_label


def build_numeric_rows(train: pd.DataFrame, test: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for feature in NUMERIC_FEATURES:
        train_series = pd.to_numeric(train[feature], errors="coerce")
        test_series = pd.to_numeric(test[feature], errors="coerce")
        rows.append(
            {
                "feature": feature,
                "feature_type": "numeric",
                "drift_metric": "psi",
                "drift_score": round(population_stability_index(train_series, test_series), 6),
                "train_mean": round(float(train_series.mean()), 6),
                "test_mean": round(float(test_series.mean()), 6),
                "train_p50": round(float(train_series.median()), 6),
                "test_p50": round(float(test_series.median()), 6),
                "train_p90": round(float(train_series.quantile(0.9)), 6),
                "test_p90": round(float(test_series.quantile(0.9)), 6),
                "note": "",
            }
        )
    return rows


def build_categorical_rows(train: pd.DataFrame, test: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for feature in CATEGORICAL_FEATURES:
        drift_score, max_gap_label = total_variation_distance(train[feature], test[feature])
        train_top = train[feature].fillna("UNKNOWN").astype(str).value_counts(normalize=True).index[0]
        test_top = test[feature].fillna("UNKNOWN").astype(str).value_counts(normalize=True).index[0]
        rows.append(
            {
                "feature": feature,
                "feature_type": "categorical",
                "drift_metric": "tv_distance",
                "drift_score": round(drift_score, 6),
                "train_mean": "",
                "test_mean": "",
                "train_p50": "",
                "test_p50": "",
                "train_p90": "",
                "test_p90": "",
                "note": f"top_train={train_top}; top_test={test_top}; max_gap_category={max_gap_label}",
            }
        )
    return rows


def write_report(path: Path, rows: list[dict[str, object]], train_rows: int, test_rows: int) -> None:
    df = pd.DataFrame(rows)
    numeric = df[df["feature_type"] == "numeric"].sort_values("drift_score", ascending=False)
    categorical = df[df["feature_type"] == "categorical"].sort_values("drift_score", ascending=False)
    lines = [
        "# Train-Test Drift Report",
        "",
        f"- Train sampled rows: {train_rows}",
        f"- Test sampled rows: {test_rows}",
        "- Numeric features use Population Stability Index (PSI).",
        "- Categorical features use total variation distance.",
        "",
    ]
    if not numeric.empty:
        lines.append("## Highest numeric drift")
        for row in numeric.head(5).to_dict(orient="records"):
            lines.append(
                f"- {row['feature']}: PSI `{row['drift_score']}` | train mean `{row['train_mean']}` -> test mean `{row['test_mean']}`"
            )
        lines.append("")
    if not categorical.empty:
        lines.append("## Categorical drift")
        for row in categorical.to_dict(orient="records"):
            lines.append(f"- {row['feature']}: TV distance `{row['drift_score']}` | {row['note']}")
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "- Moderate or high PSI features are the first candidates for retraining cadence checks and threshold review.",
            "- If drift is concentrated in weather severity or complaint-history variables, the model likely needs periodic seasonal refresh rather than a full redesign.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    train, test = collect_split_samples(Path(args.input), args.max_sample_rows, args.random_state)
    if train.empty or test.empty:
        raise ValueError("Could not collect both train and test samples from the scored CSV.")

    numeric_rows = build_numeric_rows(train, test)
    categorical_rows = build_categorical_rows(train, test)
    rows = numeric_rows + categorical_rows

    write_csv(Path(args.metrics_output), rows)
    write_report(Path(args.report_output), rows, len(train), len(test))

    print(f"wrote drift metrics to {args.metrics_output}", flush=True)
    print(f"wrote drift report to {args.report_output}", flush=True)


if __name__ == "__main__":
    main()
