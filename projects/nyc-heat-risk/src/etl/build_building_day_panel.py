from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def parse_iso_date(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    return value[:10]


def normalize_text(value: str) -> str:
    return " ".join((value or "").strip().upper().split())


def safe_int(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def compute_bbl(boroid: str, block: str, lot: str) -> str:
    boroid = (boroid or "").strip()
    block_int = safe_int(block)
    lot_int = safe_int(lot)
    if not boroid or block_int is None or lot_int is None:
        return ""
    return f"{boroid}{block_int:05d}{lot_int:04d}"


@dataclass
class ComplaintAggregate:
    building_id: str
    building_bbl: str
    complaint_date: str
    borough: str
    incident_address: str
    complaint_count: int = 0
    no_heat_count: int = 0
    no_hot_water_count: int = 0
    unique_problem_codes: set[str] | None = None
    unique_keys: set[str] | None = None

    def __post_init__(self) -> None:
        if self.unique_problem_codes is None:
            self.unique_problem_codes = set()
        if self.unique_keys is None:
            self.unique_keys = set()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def index_by_field(rows: list[dict[str, str]], field_name: str) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        key = (row.get(field_name) or "").strip()
        if key:
            index[key] = row
    return index


def is_closed_violation_status(status: str) -> bool:
    normalized = normalize_text(status)
    return "CLOSED" in normalized or "DISMISSED" in normalized


def index_violations(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str | bool]]]:
    grouped: dict[str, list[dict[str, str | bool]]] = defaultdict(list)
    for row in rows:
        building_id = (row.get("buildingid") or "").strip()
        if not building_id:
            continue
        issued_date = parse_iso_date(row.get("novissueddate", ""))
        if not issued_date:
            continue
        status = normalize_text(row.get("currentstatus", ""))
        close_date = parse_iso_date(row.get("currentstatusdate", ""))
        if is_closed_violation_status(status):
            if not close_date or close_date < issued_date:
                close_date = issued_date
        else:
            close_date = ""
        grouped[building_id].append(
            {
                "issued_date": issued_date,
                "close_date": close_date,
                "is_closed": is_closed_violation_status(status),
            }
        )
    return grouped


def build_panel(
    complaints_rows: list[dict[str, str]],
    building_index: dict[str, dict[str, str]],
    registration_index: dict[str, dict[str, str]],
    violation_index: dict[str, list[dict[str, str | bool]]],
    heat_sensor_index: dict[str, dict[str, str]],
) -> list[dict[str, str | int]]:
    grouped: dict[tuple[str, str], ComplaintAggregate] = {}

    for row in complaints_rows:
        building_id = (row.get("building_id") or "").strip()
        complaint_date = parse_iso_date(row.get("received_date", ""))
        if not building_id or not complaint_date:
            continue

        key = (building_id, complaint_date)
        aggregate = grouped.get(key)
        if aggregate is None:
            aggregate = ComplaintAggregate(
                building_id=building_id,
                building_bbl=(row.get("bbl") or "").strip(),
                complaint_date=complaint_date,
                borough=normalize_text(row.get("borough", "")),
                incident_address=normalize_text(f"{row.get('house_number', '')} {row.get('street_name', '')}"),
            )
            grouped[key] = aggregate

        aggregate.complaint_count += 1
        problem_code = normalize_text(row.get("problem_code", ""))
        unique_key = (row.get("unique_key") or "").strip()
        aggregate.unique_problem_codes.add(problem_code)
        if unique_key:
            aggregate.unique_keys.add(unique_key)
        if "NO HEAT" in problem_code:
            aggregate.no_heat_count += 1
        if "HOT WATER" in problem_code:
            aggregate.no_hot_water_count += 1

    panel_rows: list[dict[str, str | int]] = []
    grouped_aggregates: dict[str, list[ComplaintAggregate]] = defaultdict(list)
    for aggregate in grouped.values():
        grouped_aggregates[aggregate.building_id].append(aggregate)

    for building_id, building_aggregates in grouped_aggregates.items():
        building_row = building_index.get(building_id, {})
        registration_row = registration_index.get(building_id, {})
        heat_sensor_row = heat_sensor_index.get(building_id, {})
        violations = sorted(
            violation_index.get(building_id, []),
            key=lambda row: str(row["issued_date"]),
        )
        close_dates = sorted(
            str(row["close_date"])
            for row in violations
            if row.get("is_closed") and row.get("close_date")
        )

        issue_ptr = 0
        close_ptr = 0
        total_violation_count = 0
        open_violation_count = 0
        latest_violation_date = ""

        for aggregate in sorted(building_aggregates, key=lambda row: row.complaint_date):
            while issue_ptr < len(violations) and str(violations[issue_ptr]["issued_date"]) <= aggregate.complaint_date:
                total_violation_count += 1
                open_violation_count += 1
                latest_violation_date = str(violations[issue_ptr]["issued_date"])
                issue_ptr += 1

            while close_ptr < len(close_dates) and close_dates[close_ptr] <= aggregate.complaint_date:
                open_violation_count = max(0, open_violation_count - 1)
                close_ptr += 1

            building_bbl = aggregate.building_bbl or compute_bbl(
                building_row.get("boroid", ""),
                building_row.get("block", ""),
                building_row.get("lot", ""),
            )

            registration_end = parse_iso_date(registration_row.get("registrationenddate", ""))
            registration_active_flag = 1 if registration_end and registration_end >= aggregate.complaint_date else 0

            unit_count = (
                safe_int(building_row.get("legalclassa", ""))
                or safe_int(building_row.get("legalclassb", ""))
                or 0
            )

            heat_sensor_start_date = parse_iso_date(heat_sensor_row.get("program_start_date", ""))
            heat_sensor_discharge_date = parse_iso_date(heat_sensor_row.get("discharge_date", ""))
            heat_sensor_status = normalize_text(heat_sensor_row.get("current_status", ""))
            heat_sensor_program_flag = 1 if heat_sensor_row else 0
            heat_sensor_active_flag = 0
            if heat_sensor_program_flag:
                starts_before_or_on_complaint = not heat_sensor_start_date or heat_sensor_start_date <= aggregate.complaint_date
                ends_after_or_missing = not heat_sensor_discharge_date or heat_sensor_discharge_date >= aggregate.complaint_date
                if "ACTIVE" in heat_sensor_status and starts_before_or_on_complaint and ends_after_or_missing:
                    heat_sensor_active_flag = 1

            heat_sensor_unit_count = safe_int(heat_sensor_row.get("total_units", "")) or 0

            panel_rows.append(
                {
                    "building_id": aggregate.building_id,
                    "building_bbl": building_bbl,
                    "complaint_date": aggregate.complaint_date,
                    "borough": aggregate.borough,
                    "incident_address": aggregate.incident_address,
                    "complaint_count": aggregate.complaint_count,
                    "no_heat_count": aggregate.no_heat_count,
                    "hot_water_problem_count": aggregate.no_hot_water_count,
                    "problem_codes": " | ".join(sorted(code for code in aggregate.unique_problem_codes if code)),
                    "unique_request_count": len(aggregate.unique_keys),
                    "management_program": building_row.get("managementprogram", ""),
                    "building_zip": building_row.get("zip", ""),
                    "community_board": building_row.get("communityboard", ""),
                    "census_tract": building_row.get("censustract", ""),
                    "registration_id": registration_row.get("registrationid", "") or building_row.get("registrationid", ""),
                    "registration_active_flag": registration_active_flag,
                    "last_registration_date": parse_iso_date(registration_row.get("lastregistrationdate", "")),
                    "registration_end_date": registration_end,
                    "heat_sensor_program_flag": heat_sensor_program_flag,
                    "heat_sensor_active_flag": heat_sensor_active_flag,
                    "heat_sensor_program_start_date": heat_sensor_start_date,
                    "heat_sensor_discharge_date": heat_sensor_discharge_date,
                    "heat_sensor_unit_count": heat_sensor_unit_count,
                    "total_linked_violation_count": total_violation_count,
                    "open_linked_violation_count": open_violation_count,
                    "latest_linked_violation_date": latest_violation_date,
                    "unit_count_proxy": unit_count,
                }
            )

    panel_rows.sort(key=lambda row: (str(row["building_id"]), str(row["complaint_date"])))
    return panel_rows


def write_csv(path: Path, rows: list[dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the first building-day panel from the NYC heat-risk starter files."
    )
    parser.add_argument(
        "--complaints",
        default="projects/nyc-heat-risk/data/raw/hpd_complaints_and_problems_heat.csv",
        help="Path to the HPD complaints and problems heat extract.",
    )
    parser.add_argument(
        "--buildings",
        default="projects/nyc-heat-risk/data/raw/hpd_buildings_linked.csv",
        help="Path to the linked HPD buildings extract. Falls back to the sample file if missing.",
    )
    parser.add_argument(
        "--registrations",
        default="projects/nyc-heat-risk/data/raw/hpd_registrations_linked.csv",
        help="Path to the linked HPD registrations extract. Falls back to the sample file if missing.",
    )
    parser.add_argument(
        "--violations",
        default="projects/nyc-heat-risk/data/raw/hpd_violations_linked.csv",
        help="Path to the linked HPD violations extract. Falls back to the sample file if missing.",
    )
    parser.add_argument(
        "--output",
        default="projects/nyc-heat-risk/data/processed/building_day_heat_panel.csv",
        help="Output CSV path for the first building-day panel.",
    )
    parser.add_argument(
        "--heat-sensor",
        default="projects/nyc-heat-risk/data/raw/hpd_heat_sensor_program.csv",
        help="Path to the HPD Heat Sensor Program extract.",
    )
    return parser.parse_args()


def resolve_fallback(primary: str, fallback: str) -> Path:
    primary_path = Path(primary)
    return primary_path if primary_path.exists() else Path(fallback)


def main() -> None:
    args = parse_args()

    complaints_rows = read_csv(Path(args.complaints))
    building_rows = read_csv(resolve_fallback(args.buildings, "projects/nyc-heat-risk/data/raw/hpd_buildings_sample.csv"))
    registration_rows = read_csv(resolve_fallback(args.registrations, "projects/nyc-heat-risk/data/raw/hpd_registrations_sample.csv"))
    violation_rows = read_csv(resolve_fallback(args.violations, "projects/nyc-heat-risk/data/raw/hpd_violations_heat_sample.csv"))
    heat_sensor_rows = read_csv(Path(args.heat_sensor))

    building_index = index_by_field(building_rows, "buildingid")
    registration_index = index_by_field(registration_rows, "buildingid")
    violation_index = index_violations(violation_rows)
    heat_sensor_index = index_by_field(heat_sensor_rows, "building_id")

    panel_rows = build_panel(
        complaints_rows=complaints_rows,
        building_index=building_index,
        registration_index=registration_index,
        violation_index=violation_index,
        heat_sensor_index=heat_sensor_index,
    )

    output_path = Path(args.output)
    write_csv(output_path, panel_rows)

    print(f"wrote {len(panel_rows)} rows to {output_path}", flush=True)
    matched_buildings = sum(1 for row in panel_rows if row["management_program"])
    print(f"rows with linked building metadata: {matched_buildings}", flush=True)


if __name__ == "__main__":
    main()
