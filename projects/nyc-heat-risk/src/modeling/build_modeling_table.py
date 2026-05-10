from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from modeling.risk_features import LABELED_DATASET_SOURCE_COLUMNS, MODELING_TABLE_COLUMNS, prepare_feature_frame
from project_paths import FINAL_DENSE_PANEL_PATH, FINAL_MODELING_TABLE_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize a compact labeled modeling table from the dense heat-risk panel.")
    parser.add_argument(
        "--input",
        default=str(FINAL_DENSE_PANEL_PATH),
        help="Dense panel CSV path.",
    )
    parser.add_argument(
        "--output",
        default=str(FINAL_MODELING_TABLE_PATH),
        help="Output CSV path for the compact modeling table.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=250_000,
        help="Number of dense-panel rows to process per chunk.",
    )
    return parser.parse_args()


def iter_modeling_chunks(path: Path, output_path: Path, chunksize: int) -> tuple[int, int]:
    output_rows = 0
    labeled_dates: set[str] = set()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    write_header = True
    for chunk in pd.read_csv(
        path,
        low_memory=False,
        usecols=lambda column: column in LABELED_DATASET_SOURCE_COLUMNS,
        chunksize=chunksize,
    ):
        if "next_day_label_available" not in chunk.columns:
            raise ValueError("Expected next_day_label_available in dense panel input.")

        chunk = chunk[chunk["next_day_label_available"] == 1].copy()
        if chunk.empty:
            continue

        prepared = prepare_feature_frame(chunk, compute_target=True)
        modeled = prepared[MODELING_TABLE_COLUMNS].copy()
        modeled["calendar_date"] = modeled["calendar_date"].dt.strftime("%Y-%m-%d")
        modeled.to_csv(
            output_path,
            index=False,
            mode="w" if write_header else "a",
            header=write_header,
        )
        write_header = False
        output_rows += int(len(modeled))
        labeled_dates.update(modeled["calendar_date"].dropna().unique().tolist())
    return output_rows, len(labeled_dates)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Missing dense panel input: {input_path}")

    output_path = Path(args.output)
    row_count, date_count = iter_modeling_chunks(input_path, output_path=output_path, chunksize=args.chunksize)
    print(f"wrote {row_count} modeling rows across {date_count} labeled dates to {args.output}", flush=True)


if __name__ == "__main__":
    main()
