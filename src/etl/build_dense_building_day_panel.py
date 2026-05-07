from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta
from pathlib import Path


def parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def safe_int(value: str | int | None) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def safe_float(value: str | float | None) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def temporal_int(base: dict[str, str] | None, field_name: str) -> int:
    return safe_int(base.get(field_name, 0) if base else 0)


def temporal_text(base: dict[str, str] | None, field_name: str) -> str:
    return (base.get(field_name, "") if base else "") or ""


def active_on_date(start_text: str, end_text: str, current_date: date, default_flag: int) -> int:
    start_date = parse_date(start_text)
    end_date = parse_date(end_text)
    starts_before_or_on_date = start_date is None or start_date <= current_date
    ends_after_or_missing = end_date is None or end_date >= current_date
    return 1 if default_flag and starts_before_or_on_date and ends_after_or_missing else 0


def registration_active_on_date(end_text: str, current_date: date) -> int:
    end_date = parse_date(end_text)
    return 1 if end_date is not None and end_date >= current_date else 0


def normalize_tract_code(value: str) -> str:
    digits = "".join(ch for ch in (value or "").strip() if ch.isdigit())
    return digits.zfill(6) if digits else ""


def candidate_tract_codes(value: str) -> list[str]:
    raw = (value or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return []

    candidates: list[str] = []

    # Many NYC tract values arrive as decimal-stripped forms such as:
    # 458 -> 045800 and 3301 -> 003301.
    if len(digits) <= 6:
        candidates.append(digits.zfill(6))
    if len(digits) <= 4:
        candidates.append((digits + "00").zfill(6))

    if "." in raw:
        left, right = raw.split(".", 1)
        left_digits = "".join(ch for ch in left if ch.isdigit())
        right_digits = "".join(ch for ch in right if ch.isdigit())[:2].ljust(2, "0")
        if left_digits or right_digits:
            candidates.append((left_digits + right_digits).zfill(6))

    unique_candidates: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates


def build_cre_index(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    index: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        borough = (row.get("borough") or "").strip().upper()
        tract_code = normalize_tract_code(row.get("tract_code") or row.get("tract") or "")
        if borough and tract_code:
            index.setdefault(borough, {})[tract_code] = row
    return index


def resolve_cre_row(
    borough: str,
    census_tract: str,
    cre_index: dict[str, dict[str, dict[str, str]]],
) -> tuple[str, dict[str, str]]:
    borough_key = (borough or "").strip().upper()
    borough_rows = cre_index.get(borough_key, {})
    for tract_code in candidate_tract_codes(census_tract):
        cre_row = borough_rows.get(tract_code)
        if cre_row:
            return tract_code, cre_row
    return "", {}


def build_dense_rows(
    rows: list[dict[str, str]],
    weather_rows: list[dict[str, str]],
    cre_rows: list[dict[str, str]],
    start: date | None,
    end: date | None,
) -> list[dict[str, str | int | float]]:
    by_building: dict[str, list[dict[str, str]]] = {}
    all_dates: list[date] = []
    weather_by_date = {(row.get("date") or "").strip(): row for row in weather_rows if (row.get("date") or "").strip()}
    cre_index = build_cre_index(cre_rows)

    for row in rows:
        building_id = (row.get("building_id") or "").strip()
        complaint_date = parse_date(row.get("complaint_date", ""))
        if not building_id or complaint_date is None:
            continue
        by_building.setdefault(building_id, []).append(row)
        all_dates.append(complaint_date)

    if not by_building:
        return []

    panel_start = start or min(all_dates)
    panel_end = end or max(all_dates)

    dense_rows: list[dict[str, str | int | float]] = []
    for building_id, building_rows in sorted(by_building.items()):
        building_rows = sorted(building_rows, key=lambda row: parse_date(row["complaint_date"]) or date.min)
        building_rows_by_date = {parse_date(row["complaint_date"]): row for row in building_rows}
        static_base = building_rows[0]
        latest_asof_row: dict[str, str] | None = None
        rolling_window: list[int] = []
        daily_counts: list[int] = []
        daily_request_counts: list[int] = []
        previous_complaint_date: date | None = None
        cumulative_complaints_prior = 0
        cumulative_request_count_prior = 0

        for current_date in daterange(panel_start, panel_end):
            source_row = building_rows_by_date.get(current_date)
            if source_row is not None:
                latest_asof_row = source_row

            complaint_count = int(source_row["complaint_count"]) if source_row else 0
            unique_request_count = int(source_row["unique_request_count"]) if source_row and source_row.get("unique_request_count") else 0
            no_heat_count = int(source_row["no_heat_count"]) if source_row and source_row.get("no_heat_count") else 0
            hot_water_problem_count = (
                int(source_row["hot_water_problem_count"])
                if source_row and source_row.get("hot_water_problem_count")
                else 0
            )
            rolling_window.append(complaint_count)
            if len(rolling_window) > 7:
                rolling_window.pop(0)

            next_date = current_date + timedelta(days=1)
            next_row = building_rows_by_date.get(next_date)
            next_day_complaint_count = int(next_row["complaint_count"]) if next_row else 0
            next_day_label_available = 1 if current_date < panel_end else 0
            complaint_day_count_prior = sum(1 for value in daily_counts if value > 0)
            rolling_3d_complaints = sum(rolling_window[-3:])
            rolling_7d_request_count = sum(daily_request_counts[-6:]) + unique_request_count
            prior_max_daily_complaints = max(daily_counts) if daily_counts else 0
            days_since_last_complaint = (current_date - previous_complaint_date).days if previous_complaint_date else -1
            weather_row = weather_by_date.get(current_date.isoformat(), {})
            tract_code, cre_row = resolve_cre_row(
                static_base.get("borough", ""),
                static_base.get("census_tract", ""),
                cre_index,
            )
            cre_pred0_pe = safe_float(cre_row.get("PRED0_PE"))
            cre_pred3_pe = safe_float(cre_row.get("PRED3_PE"))
            cre_pred12_pe = safe_float(cre_row.get("PRED12_PE"))
            cre_population = safe_int(cre_row.get("POPUNI"))
            cre_vulnerability_index = round((0.5 * cre_pred12_pe + 1.0 * cre_pred3_pe) / 100.0, 6)
            cre_high_vulnerability_flag = 1 if cre_pred3_pe >= 30.0 else 0

            temporal_base = latest_asof_row
            asof_source_date = temporal_text(temporal_base, "complaint_date")
            registration_active_flag = registration_active_on_date(static_base.get("registration_end_date", ""), current_date)
            heat_sensor_program_flag = safe_int(static_base.get("heat_sensor_program_flag"))
            heat_sensor_active_flag = active_on_date(
                static_base.get("heat_sensor_program_start_date", ""),
                static_base.get("heat_sensor_discharge_date", ""),
                current_date,
                default_flag=heat_sensor_program_flag,
            )

            dense_rows.append(
                {
                    "building_id": building_id,
                    "building_bbl": static_base.get("building_bbl", ""),
                    "calendar_date": current_date.isoformat(),
                    "borough": static_base.get("borough", ""),
                    "incident_address": static_base.get("incident_address", ""),
                    "complaint_count": complaint_count,
                    "unique_request_count": unique_request_count,
                    "no_heat_count": no_heat_count,
                    "hot_water_problem_count": hot_water_problem_count,
                    "lag_1_complaints": daily_counts[-1] if daily_counts else 0,
                    "rolling_3d_complaints": rolling_3d_complaints,
                    "rolling_7d_complaints": sum(rolling_window),
                    "rolling_7d_request_count": rolling_7d_request_count,
                    "complaint_day_count_prior": complaint_day_count_prior,
                    "cumulative_complaints_prior": cumulative_complaints_prior,
                    "cumulative_request_count_prior": cumulative_request_count_prior,
                    "prior_max_daily_complaints": prior_max_daily_complaints,
                    "days_since_last_complaint": days_since_last_complaint,
                    "next_day_complaint_count": next_day_complaint_count,
                    "next_day_label_available": next_day_label_available,
                    "surge_flag": 1 if next_day_complaint_count >= 1 else 0,
                    "management_program": static_base.get("management_program", ""),
                    "building_zip": static_base.get("building_zip", ""),
                    "community_board": static_base.get("community_board", ""),
                    "census_tract": static_base.get("census_tract", ""),
                    "cre_tract_code": tract_code,
                    "cre_coverage_flag": 1 if cre_row else 0,
                    "cre_population": cre_population,
                    "cre_pred0_pe": cre_pred0_pe,
                    "cre_pred3_pe": cre_pred3_pe,
                    "cre_pred12_pe": cre_pred12_pe,
                    "cre_vulnerability_index": cre_vulnerability_index,
                    "cre_high_vulnerability_flag": cre_high_vulnerability_flag,
                    "registration_active_flag": registration_active_flag,
                    "heat_sensor_program_flag": heat_sensor_program_flag,
                    "heat_sensor_active_flag": heat_sensor_active_flag,
                    "heat_sensor_unit_count": safe_int(static_base.get("heat_sensor_unit_count")),
                    "total_linked_violation_count": temporal_int(temporal_base, "total_linked_violation_count"),
                    "open_linked_violation_count": temporal_int(temporal_base, "open_linked_violation_count"),
                    "latest_linked_violation_date": temporal_text(temporal_base, "latest_linked_violation_date"),
                    "as_of_source_date": asof_source_date,
                    "as_of_snapshot_available_flag": 1 if temporal_base else 0,
                    "unit_count_proxy": safe_int(static_base.get("unit_count_proxy")),
                    "weather_station_count": int(weather_row.get("weather_station_count", 0) or 0),
                    "weather_avg_temp_c": float(weather_row.get("weather_avg_temp_c", 0) or 0),
                    "weather_max_temp_c": float(weather_row.get("weather_max_temp_c", 0) or 0),
                    "weather_min_temp_c": float(weather_row.get("weather_min_temp_c", 0) or 0),
                    "weather_prcp_mm_mean": float(weather_row.get("weather_prcp_mm_mean", 0) or 0),
                    "weather_prcp_mm_max": float(weather_row.get("weather_prcp_mm_max", 0) or 0),
                    "weather_wind_mps_mean": float(weather_row.get("weather_wind_mps_mean", 0) or 0),
                    "weather_heating_degree_c": float(weather_row.get("weather_heating_degree_c", 0) or 0),
                    "weather_freezing_station_count": int(weather_row.get("weather_freezing_station_count", 0) or 0),
                    "weather_freezing_any_flag": int(weather_row.get("weather_freezing_any_flag", 0) or 0),
                    "weather_temp_drop_c": float(weather_row.get("weather_temp_drop_c", 0) or 0),
                    "weather_cold_shock_flag": int(weather_row.get("weather_cold_shock_flag", 0) or 0),
                }
            )
            daily_counts.append(complaint_count)
            daily_request_counts.append(unique_request_count)
            cumulative_complaints_prior += complaint_count
            cumulative_request_count_prior += unique_request_count
            if complaint_count > 0:
                previous_complaint_date = current_date

    return dense_rows


def write_csv(path: Path, rows: list[dict[str, str | int | float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand the sparse complaint panel into a dense building-day panel.")
    parser.add_argument(
        "--input",
        default="projects/nyc-heat-risk/data/processed/building_day_heat_panel.csv",
        help="Sparse building-day panel path.",
    )
    parser.add_argument(
        "--output",
        default="projects/nyc-heat-risk/data/processed/building_day_heat_panel_dense.csv",
        help="Dense building-day panel path.",
    )
    parser.add_argument(
        "--date-from",
        default=None,
        help="Optional panel start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--date-to",
        default=None,
        help="Optional panel end date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--weather",
        default="projects/nyc-heat-risk/data/processed/noaa_gsod_nyc_daily_summary.csv",
        help="Optional NOAA daily weather summary CSV.",
    )
    parser.add_argument(
        "--cre",
        default="projects/nyc-heat-risk/data/raw/census_cre_nyc_tract_2024.csv",
        help="Optional tract-level Census CRE CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(Path(args.input))
    weather_rows = read_csv(Path(args.weather))
    cre_rows = read_csv(Path(args.cre))
    dense_rows = build_dense_rows(
        rows,
        weather_rows,
        cre_rows,
        start=parse_date(args.date_from) if args.date_from else None,
        end=parse_date(args.date_to) if args.date_to else None,
    )
    output_path = Path(args.output)
    write_csv(output_path, dense_rows)
    print(f"wrote {len(dense_rows)} rows to {output_path}", flush=True)


if __name__ == "__main__":
    main()
