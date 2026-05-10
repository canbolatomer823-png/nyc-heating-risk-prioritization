from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen


STATIONS = {
    "LGA": {
        "ghcn_id": "USW00014732",
        "name": "LAGUARDIA AIRPORT, NY US",
    },
    "JFK": {
        "ghcn_id": "USW00094789",
        "name": "JFK INTERNATIONAL AIRPORT, NY US",
    },
}

ELEMENTS = {"TMAX", "TMIN", "PRCP", "AWND"}


def ghcn_temp_to_c(value: int) -> float:
    return value / 10.0


def ghcn_prcp_to_mm(value: int) -> float:
    return value / 10.0


def ghcn_awnd_to_mps(value: int) -> float:
    return value / 10.0


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def read_station_lines(ghcn_id: str) -> list[str]:
    url = f"https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/{ghcn_id}.dly"
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore").splitlines()


def extract_daily_records(lines: list[str], station_key: str, start_date: str, end_date: str) -> list[dict[str, str | int | float]]:
    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)
    records_by_date: dict[str, dict[str, str | int | float]] = {}

    for line in lines:
        year = int(line[11:15])
        month = int(line[15:17])
        element = line[17:21]
        if element not in ELEMENTS:
            continue
        for day in range(31):
            base = 21 + day * 8
            value_text = line[base : base + 5]
            try:
                value = int(value_text)
            except Exception:
                continue
            if value == -9999:
                continue
            try:
                current_dt = datetime(year, month, day + 1)
            except ValueError:
                continue
            if current_dt < start_dt or current_dt > end_dt:
                continue
            date_key = current_dt.strftime("%Y-%m-%d")
            row = records_by_date.setdefault(
                date_key,
                {
                    "station_key": station_key,
                    "date": date_key,
                    "tmax_c": None,
                    "tmin_c": None,
                    "prcp_mm": 0.0,
                    "wind_mps": 0.0,
                },
            )
            if element == "TMAX":
                row["tmax_c"] = ghcn_temp_to_c(value)
            elif element == "TMIN":
                row["tmin_c"] = ghcn_temp_to_c(value)
            elif element == "PRCP":
                row["prcp_mm"] = ghcn_prcp_to_mm(value)
            elif element == "AWND":
                row["wind_mps"] = ghcn_awnd_to_mps(value)

    processed: list[dict[str, str | int | float]] = []
    for date_key in sorted(records_by_date):
        row = records_by_date[date_key]
        tmax_c = row["tmax_c"]
        tmin_c = row["tmin_c"]
        if tmax_c is None or tmin_c is None:
            continue
        avg_temp_c = (float(tmax_c) + float(tmin_c)) / 2.0
        processed.append(
            {
                "station_key": station_key,
                "station_id": STATIONS[station_key]["ghcn_id"],
                "station_name": STATIONS[station_key]["name"],
                "date": date_key,
                "avg_temp_c": round(avg_temp_c, 4),
                "max_temp_c": round(float(tmax_c), 4),
                "min_temp_c": round(float(tmin_c), 4),
                "prcp_mm": round(float(row["prcp_mm"]), 4),
                "wind_mps": round(float(row["wind_mps"]), 4),
                "freezing_flag": 1 if float(tmin_c) <= 0.0 else 0,
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


def write_csv(path: Path, rows: list[dict[str, str | int | float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def latest_station_date(rows: list[dict[str, str | int | float]]) -> str:
    return max(str(row["date"]) for row in rows) if rows else "n/a"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and summarize official NOAA GHCN-Daily weather for NYC heat-risk windows.")
    parser.add_argument("--date-from", required=True, help="Inclusive lower bound date in YYYY-MM-DD format.")
    parser.add_argument("--date-to", required=True, help="Inclusive upper bound date in YYYY-MM-DD format.")
    parser.add_argument(
        "--station-output",
        default="projects/nyc-heat-risk/data/raw/noaa_ghcn_nyc_station_daily.csv",
        help="Path for per-station filtered daily rows.",
    )
    parser.add_argument(
        "--summary-output",
        default="projects/nyc-heat-risk/data/processed/noaa_ghcn_nyc_daily_summary.csv",
        help="Path for aggregated NYC daily weather summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    station_rows: list[dict[str, str | int | float]] = []
    for station_key, meta in STATIONS.items():
        lines = read_station_lines(meta["ghcn_id"])
        station_rows.extend(extract_daily_records(lines, station_key, args.date_from, args.date_to))

    if not station_rows:
        raise ValueError("No NOAA GHCN-Daily station rows were found for the requested window.")

    summary_rows = aggregate_daily_summary(station_rows)
    if not summary_rows:
        raise ValueError("NOAA GHCN-Daily summary rows are empty for the requested window.")

    write_csv(Path(args.station_output), station_rows)
    write_csv(Path(args.summary_output), summary_rows)
    print(f"wrote station weather rows to {args.station_output}", flush=True)
    print(f"wrote daily weather summary to {args.summary_output}", flush=True)
    print(f"latest station date in output: {latest_station_date(station_rows)}", flush=True)


if __name__ == "__main__":
    main()
