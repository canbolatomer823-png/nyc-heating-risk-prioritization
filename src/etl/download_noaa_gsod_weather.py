from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from io import StringIO
from pathlib import Path
from urllib.request import urlopen


STATIONS = {
    "LGA": {
        "station_id": "72503014732",
        "name": "LAGUARDIA AIRPORT, NY US",
    },
    "JFK": {
        "station_id": "74486094789",
        "name": "JFK INTERNATIONAL AIRPORT, NY US",
    },
}


def fahrenheit_to_celsius(value: float) -> float:
    return (value - 32.0) * 5.0 / 9.0


def inches_to_mm(value: float) -> float:
    return value * 25.4


def knots_to_mps(value: float) -> float:
    return value * 0.514444


def safe_float(value: str | None, missing_sentinel: float | None = None) -> float | None:
    try:
        parsed = float((value or "").strip())
    except Exception:
        return None
    if missing_sentinel is not None and abs(parsed - missing_sentinel) < 1e-9:
        return None
    return parsed


def date_year(value: str) -> int:
    return datetime.strptime(value[:10], "%Y-%m-%d").year


def years_in_window(start_date: str, end_date: str) -> list[int]:
    start_year = date_year(start_date)
    end_year = date_year(end_date)
    return list(range(start_year, end_year + 1))


def read_station_rows(station_id: str, year: int) -> list[dict[str, str]]:
    url = f"https://noaa-gsod-pds.s3.amazonaws.com/{year}/{station_id}.csv"
    with urlopen(url, timeout=20) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(StringIO(text)))


def filter_date_window(rows: list[dict[str, str]], start_date: str, end_date: str) -> list[dict[str, str]]:
    return [row for row in rows if start_date <= (row.get("DATE") or "") <= end_date]


def write_csv(path: Path, rows: list[dict[str, str | int | float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_station_rows(station_key: str, rows: list[dict[str, str]]) -> list[dict[str, str | int | float]]:
    station_meta = STATIONS[station_key]
    processed: list[dict[str, str | int | float]] = []
    for row in rows:
        avg_temp_f = safe_float(row.get("TEMP"), 9999.9)
        max_temp_f = safe_float(row.get("MAX"), 9999.9)
        min_temp_f = safe_float(row.get("MIN"), 9999.9)
        prcp_in = safe_float(row.get("PRCP"), 99.99)
        wind_knots = safe_float(row.get("WDSP"), 999.9)

        if avg_temp_f is None or max_temp_f is None or min_temp_f is None:
            continue

        processed.append(
            {
                "station_key": station_key,
                "station_id": station_meta["station_id"],
                "station_name": station_meta["name"],
                "date": row.get("DATE", ""),
                "avg_temp_c": round(fahrenheit_to_celsius(avg_temp_f), 4),
                "max_temp_c": round(fahrenheit_to_celsius(max_temp_f), 4),
                "min_temp_c": round(fahrenheit_to_celsius(min_temp_f), 4),
                "prcp_mm": round(inches_to_mm(prcp_in or 0.0), 4),
                "wind_mps": round(knots_to_mps(wind_knots or 0.0), 4),
                "freezing_flag": 1 if min_temp_f <= 32.0 else 0,
            }
        )
    return processed


def aggregate_daily_summary(rows: list[dict[str, str | int | float]]) -> list[dict[str, str | int | float]]:
    grouped: dict[str, list[dict[str, str | int | float]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["date"])].append(row)

    summary_rows: list[dict[str, str | int | float]] = []
    previous_avg_temp_c: float | None = None
    for date_key in sorted(grouped):
        date_rows = grouped[date_key]
        station_count = len(date_rows)
        avg_temp_c = sum(float(row["avg_temp_c"]) for row in date_rows) / station_count
        max_temp_c = sum(float(row["max_temp_c"]) for row in date_rows) / station_count
        min_temp_c = sum(float(row["min_temp_c"]) for row in date_rows) / station_count
        prcp_mm_mean = sum(float(row["prcp_mm"]) for row in date_rows) / station_count
        prcp_mm_max = max(float(row["prcp_mm"]) for row in date_rows)
        wind_mps_mean = sum(float(row["wind_mps"]) for row in date_rows) / station_count
        freezing_station_count = sum(int(row["freezing_flag"]) for row in date_rows)
        heating_degree_c = max(18.0 - avg_temp_c, 0.0)
        temp_drop_c = (previous_avg_temp_c - avg_temp_c) if previous_avg_temp_c is not None else 0.0

        summary_rows.append(
            {
                "date": date_key,
                "weather_station_count": station_count,
                "weather_avg_temp_c": round(avg_temp_c, 4),
                "weather_max_temp_c": round(max_temp_c, 4),
                "weather_min_temp_c": round(min_temp_c, 4),
                "weather_prcp_mm_mean": round(prcp_mm_mean, 4),
                "weather_prcp_mm_max": round(prcp_mm_max, 4),
                "weather_wind_mps_mean": round(wind_mps_mean, 4),
                "weather_heating_degree_c": round(heating_degree_c, 4),
                "weather_freezing_station_count": freezing_station_count,
                "weather_freezing_any_flag": 1 if freezing_station_count > 0 else 0,
                "weather_temp_drop_c": round(temp_drop_c, 4),
                "weather_cold_shock_flag": 1 if temp_drop_c >= 3.0 else 0,
            }
        )
        previous_avg_temp_c = avg_temp_c

    return summary_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and summarize official NOAA GSOD weather for the NYC heat-risk project.")
    parser.add_argument(
        "--date-from",
        default="2025-01-01",
        help="Inclusive lower bound date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--date-to",
        default="2025-01-07",
        help="Inclusive upper bound date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--station-output",
        default="projects/nyc-heat-risk/data/raw/noaa_gsod_nyc_station_daily.csv",
        help="Path for per-station filtered daily rows.",
    )
    parser.add_argument(
        "--summary-output",
        default="projects/nyc-heat-risk/data/processed/noaa_gsod_nyc_daily_summary.csv",
        help="Path for aggregated NYC daily weather summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    station_rows: list[dict[str, str | int | float]] = []
    year_values = years_in_window(args.date_from, args.date_to)
    for station_key, station_meta in STATIONS.items():
        station_window_rows: list[dict[str, str]] = []
        for year in year_values:
            raw_rows = read_station_rows(station_meta["station_id"], year)
            station_window_rows.extend(filter_date_window(raw_rows, args.date_from, args.date_to))
        station_rows.extend(build_station_rows(station_key, station_window_rows))

    if not station_rows:
        raise ValueError(
            "No NOAA GSOD station rows were found for the requested window. "
            "This usually means the chosen dates are not yet covered by the GSOD publication lag "
            "for the configured stations."
        )

    summary_rows = aggregate_daily_summary(station_rows)
    if not summary_rows:
        raise ValueError("NOAA GSOD summary rows are empty for the requested window.")
    write_csv(Path(args.station_output), station_rows)
    write_csv(Path(args.summary_output), summary_rows)
    print(f"wrote station weather rows to {args.station_output}", flush=True)
    print(f"wrote daily weather summary to {args.summary_output}", flush=True)


if __name__ == "__main__":
    main()
