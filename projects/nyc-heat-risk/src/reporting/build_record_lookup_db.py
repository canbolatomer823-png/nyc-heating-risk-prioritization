from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from api.app import PRIORITY_COLUMNS, PRIORITY_NUMERIC_COLUMNS, STRING_COLUMNS, normalize_priority_frame
from project_paths import FINAL_RECORD_LOOKUP_DB_PATH, FINAL_SCORED_CSV_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an indexed SQLite lookup artifact from the scored CSV.")
    parser.add_argument(
        "--input",
        default=str(FINAL_SCORED_CSV_PATH),
        help="Scored CSV path.",
    )
    parser.add_argument(
        "--output",
        default=str(FINAL_RECORD_LOOKUP_DB_PATH),
        help="SQLite output path.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100_000,
        help="Number of scored rows to process per chunk.",
    )
    return parser.parse_args()


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        DROP TABLE IF EXISTS record_lookup;
        CREATE TABLE record_lookup (
            calendar_date TEXT NOT NULL,
            building_id TEXT NOT NULL,
            building_bbl TEXT,
            borough TEXT,
            incident_address TEXT,
            model_probability REAL,
            model_prediction INTEGER,
            model_threshold REAL,
            open_linked_violation_count REAL,
            cumulative_complaints_prior REAL,
            heat_sensor_active_flag REAL,
            management_program TEXT
        );
        """
    )
    connection.commit()


def insert_chunk(connection: sqlite3.Connection, frame: pd.DataFrame) -> int:
    normalized = normalize_priority_frame(frame[PRIORITY_COLUMNS].copy())
    records = [
        (
            str(row["calendar_date"]),
            str(row["building_id"]),
            str(row.get("building_bbl", "") or ""),
            str(row.get("borough", "") or ""),
            str(row.get("incident_address", "") or ""),
            float(row.get("model_probability", 0.0) or 0.0),
            int(row.get("model_prediction", 0) or 0),
            float(row.get("model_threshold", 0.0) or 0.0),
            float(row.get("open_linked_violation_count", 0.0) or 0.0),
            float(row.get("cumulative_complaints_prior", 0.0) or 0.0),
            float(row.get("heat_sensor_active_flag", 0.0) or 0.0),
            str(row.get("management_program", "") or ""),
        )
        for row in normalized.to_dict(orient="records")
    ]
    connection.executemany(
        """
        INSERT INTO record_lookup (
            calendar_date,
            building_id,
            building_bbl,
            borough,
            incident_address,
            model_probability,
            model_prediction,
            model_threshold,
            open_linked_violation_count,
            cumulative_complaints_prior,
            heat_sensor_active_flag,
            management_program
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )
    connection.commit()
    return len(records)


def finalize_db(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE INDEX idx_record_lookup_building_date
        ON record_lookup (building_id, calendar_date);
        CREATE INDEX idx_record_lookup_date_probability
        ON record_lookup (calendar_date, model_probability DESC);
        """
    )
    connection.commit()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Missing scored CSV input: {input_path}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    dtype_map = {column: "string" for column in STRING_COLUMNS}
    for column in PRIORITY_NUMERIC_COLUMNS:
        dtype_map[column] = "float64"

    total_rows = 0
    with sqlite3.connect(output_path) as connection:
        init_db(connection)
        for chunk in pd.read_csv(
            input_path,
            usecols=PRIORITY_COLUMNS,
            chunksize=args.chunksize,
            low_memory=False,
            dtype=dtype_map,
        ):
            total_rows += insert_chunk(connection, chunk)
        finalize_db(connection)

    print(f"wrote {total_rows} record lookup rows to {output_path}", flush=True)


if __name__ == "__main__":
    main()
