from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_int(value: str | None) -> int:
    try:
        return int(value or "0")
    except Exception:
        return 0


def profile_complaints(rows: list[dict[str, str]]) -> str:
    building_ids = {(row.get("building_id") or "").strip() for row in rows if (row.get("building_id") or "").strip()}
    dates = sorted(
        ((row.get("received_date") or row.get("complaint_date") or "")[:10])
        for row in rows
        if (row.get("received_date") or row.get("complaint_date"))
    )
    problem_codes = Counter(
        (row.get("problem_code") or row.get("problem_codes") or "").strip()
        for row in rows
    )
    boroughs = Counter((row.get("borough") or "").strip() for row in rows)

    lines = [
        "# Heat Data Profile",
        "",
        "## Complaint extract",
        f"- Row count: {len(rows)}",
        f"- Unique building_id count: {len(building_ids)}",
        f"- Date range: {dates[0] if dates else 'n/a'} -> {dates[-1] if dates else 'n/a'}",
        "",
        "### Top problem codes",
    ]
    for code, count in problem_codes.most_common(10):
        lines.append(f"- {code}: {count}")

    lines.append("")
    lines.append("### Borough distribution")
    for borough, count in boroughs.most_common():
        lines.append(f"- {borough}: {count}")
    lines.append("")
    return "\n".join(lines)


def profile_dense_panel(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "## Dense panel\n- No rows available.\n"

    building_ids = {(row.get("building_id") or "").strip() for row in rows if (row.get("building_id") or "").strip()}
    dates = sorted((row.get("calendar_date") or "") for row in rows if row.get("calendar_date"))
    positive_days = sum(safe_int(row.get("complaint_count")) > 0 for row in rows)
    surge_days = sum(safe_int(row.get("surge_flag")) > 0 for row in rows)
    labeled_rows = sum(safe_int(row.get("next_day_label_available")) > 0 for row in rows)
    total_open_violations = sum(safe_int(row.get("open_linked_violation_count")) for row in rows)
    heat_sensor_buildings = {
        (row.get("building_id") or "").strip()
        for row in rows
        if safe_int(row.get("heat_sensor_program_flag")) > 0 and (row.get("building_id") or "").strip()
    }
    active_heat_sensor_days = sum(safe_int(row.get("heat_sensor_active_flag")) > 0 for row in rows)
    chronic_high_prior = sum(safe_int(row.get("cumulative_complaints_prior")) >= 5 for row in rows)
    weather_coverage_rows = sum(safe_int(row.get("weather_station_count")) > 0 for row in rows)
    weather_avg_temps = [
        float(row.get("weather_avg_temp_c") or 0)
        for row in rows
        if safe_int(row.get("weather_station_count")) > 0
    ]
    freezing_rows = sum(safe_int(row.get("weather_freezing_any_flag")) > 0 for row in rows)
    cre_coverage_rows = sum(safe_int(row.get("cre_coverage_flag")) > 0 for row in rows)
    cre_high_vulnerability_rows = sum(safe_int(row.get("cre_high_vulnerability_flag")) > 0 for row in rows)
    cre_vulnerability_values = [
        float(row.get("cre_vulnerability_index") or 0)
        for row in rows
        if safe_int(row.get("cre_coverage_flag")) > 0
    ]
    positive_risk_scores = Counter(
        "high" if safe_int(row.get("rolling_7d_complaints")) >= 3 else "low"
        for row in rows
    )

    lines = [
        "## Dense panel",
        f"- Row count: {len(rows)}",
        f"- Unique building count: {len(building_ids)}",
        f"- Date range: {dates[0] if dates else 'n/a'} -> {dates[-1] if dates else 'n/a'}",
        f"- Positive complaint days: {positive_days}",
        f"- Next-day surge positives: {surge_days}",
        f"- Rows with valid next-day labels: {labeled_rows}",
        f"- Total open linked violations carried into panel: {total_open_violations}",
        f"- Heat Sensor Program building count: {len(heat_sensor_buildings)}",
        f"- Active Heat Sensor Program row count: {active_heat_sensor_days}",
        f"- Weather-covered row count: {weather_coverage_rows}",
        f"- Weather avg temp range (C): {round(min(weather_avg_temps), 2) if weather_avg_temps else 'n/a'} -> {round(max(weather_avg_temps), 2) if weather_avg_temps else 'n/a'}",
        f"- Weather freezing rows: {freezing_rows}",
        f"- CRE-covered row count: {cre_coverage_rows}",
        f"- CRE high-vulnerability row count: {cre_high_vulnerability_rows}",
        f"- CRE vulnerability index range: {round(min(cre_vulnerability_values), 4) if cre_vulnerability_values else 'n/a'} -> {round(max(cre_vulnerability_values), 4) if cre_vulnerability_values else 'n/a'}",
        "",
        "### Rolling 7-day complaint buckets",
        f"- High (>=3 complaints): {positive_risk_scores['high']}",
        f"- Low (<3 complaints): {positive_risk_scores['low']}",
        "",
        "### Chronicity buckets",
        f"- Rows with cumulative prior complaints >= 5: {chronic_high_prior}",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile the current NYC heat-risk extracts and dense panel.")
    parser.add_argument(
        "--complaints",
        default="projects/nyc-heat-risk/data/raw/hpd_complaints_and_problems_heat.csv",
        help="Complaint extract path.",
    )
    parser.add_argument(
        "--dense-panel",
        default="projects/nyc-heat-risk/data/processed/building_day_heat_panel_dense.csv",
        help="Dense panel path.",
    )
    parser.add_argument(
        "--output",
        default="projects/nyc-heat-risk/reports/heat_data_profile.md",
        help="Markdown output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    complaint_rows = read_csv(Path(args.complaints))
    dense_rows = read_csv(Path(args.dense_panel))

    report = "\n".join([profile_complaints(complaint_rows), profile_dense_panel(dense_rows)])
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote profile report to {output_path}", flush=True)


if __name__ == "__main__":
    main()
