from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ETL_ROOT = PROJECT_ROOT / "src" / "etl"
WORKSPACE_ROOT = PROJECT_ROOT.parents[1]


def run_step(name: str, command: list[str]) -> None:
    print(f"[window-build] {name}", flush=True)
    print(f"[window-build] cmd: {' '.join(command)}", flush=True)
    subprocess.run(command, check=True)


def resolve_python_executable() -> str:
    explicit = os.environ.get("PYTHON_EXECUTABLE")
    if explicit:
        return explicit
    venv_python = WORKSPACE_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build raw and processed artifacts for a named NYC heating complaint data window."
    )
    parser.add_argument("--window-name", required=True, help="Folder-safe name for the output window.")
    parser.add_argument("--date-from", required=True, help="Inclusive lower bound date in YYYY-MM-DD format.")
    parser.add_argument("--date-to", required=True, help="Inclusive upper bound date in YYYY-MM-DD format.")
    parser.add_argument(
        "--extract-limit",
        type=int,
        default=300000,
        help="Row limit for the filtered 311 and HPD complaint extracts.",
    )
    parser.add_argument(
        "--reference-limit",
        type=int,
        default=5000,
        help="Row limit for fallback/reference datasets such as sample building pulls.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=300,
        help="Maximum number of building ids per linked HPD request batch.",
    )
    parser.add_argument(
        "--weather-source",
        choices=["gsod", "ghcn"],
        default="gsod",
        help="Official NOAA daily weather source to use for the window.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    window_root = PROJECT_ROOT / "data" / "windows" / args.window_name
    raw_dir = window_root / "raw"
    processed_dir = window_root / "processed"
    reports_dir = window_root / "reports"

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    python_executable = resolve_python_executable()
    weather_source = args.weather_source
    weather_script_name = "download_noaa_gsod_weather.py" if weather_source == "gsod" else "download_noaa_ghcn_daily_weather.py"
    weather_station_filename = f"noaa_{weather_source}_nyc_station_daily.csv"
    weather_summary_filename = f"noaa_{weather_source}_nyc_daily_summary.csv"

    run_step(
        "download-official-data",
        [
            python_executable,
            str(ETL_ROOT / "download_official_data.py"),
            "--date-from",
            args.date_from,
            "--date-to",
            args.date_to,
            "--extract-limit",
            str(args.extract_limit),
            "--reference-limit",
            str(args.reference_limit),
            "--skip-support-downloads",
            "--output-dir",
            str(raw_dir),
            "--manifest",
            str(raw_dir / "download_manifest.json"),
        ],
    )
    run_step(
        "download-noaa-weather",
        [
            python_executable,
            str(ETL_ROOT / weather_script_name),
            "--date-from",
            args.date_from,
            "--date-to",
            args.date_to,
            "--station-output",
            str(raw_dir / weather_station_filename),
            "--summary-output",
            str(processed_dir / weather_summary_filename),
        ],
    )
    run_step(
        "download-nyc-cre-tracts",
        [
            python_executable,
            str(ETL_ROOT / "download_nyc_cre_tracts.py"),
            "--output",
            str(raw_dir / "census_cre_nyc_tract_2024.csv"),
        ],
    )
    run_step(
        "download-linked-hpd",
        [
            python_executable,
            str(ETL_ROOT / "download_linked_hpd_data.py"),
            "--complaints-path",
            str(raw_dir / "hpd_complaints_and_problems_heat.csv"),
            "--output-dir",
            str(raw_dir),
            "--manifest",
            str(raw_dir / "linked_download_manifest.json"),
            "--batch-size",
            str(args.batch_size),
        ],
    )
    run_step(
        "build-sparse-panel",
        [
            python_executable,
            str(ETL_ROOT / "build_building_day_panel.py"),
            "--complaints",
            str(raw_dir / "hpd_complaints_and_problems_heat.csv"),
            "--buildings",
            str(raw_dir / "hpd_buildings_linked.csv"),
            "--registrations",
            str(raw_dir / "hpd_registrations_linked.csv"),
            "--violations",
            str(raw_dir / "hpd_violations_linked.csv"),
            "--heat-sensor",
            str(raw_dir / "hpd_heat_sensor_program.csv"),
            "--output",
            str(processed_dir / "building_day_heat_panel.csv"),
        ],
    )
    run_step(
        "build-dense-panel",
        [
            python_executable,
            str(ETL_ROOT / "build_dense_building_day_panel.py"),
            "--input",
            str(processed_dir / "building_day_heat_panel.csv"),
            "--output",
            str(processed_dir / "building_day_heat_panel_dense.csv"),
            "--weather",
            str(processed_dir / weather_summary_filename),
            "--cre",
            str(raw_dir / "census_cre_nyc_tract_2024.csv"),
            "--date-from",
            args.date_from,
            "--date-to",
            args.date_to,
        ],
    )
    run_step(
        "profile-window",
        [
            python_executable,
            str(ETL_ROOT / "profile_heat_data.py"),
            "--complaints",
            str(raw_dir / "hpd_complaints_and_problems_heat.csv"),
            "--dense-panel",
            str(processed_dir / "building_day_heat_panel_dense.csv"),
            "--output",
            str(reports_dir / "heat_data_profile.md"),
        ],
    )
    run_step(
        "audit-window-quality",
        [
            python_executable,
            str(ETL_ROOT / "audit_panel_quality.py"),
            "--sparse-panel",
            str(processed_dir / "building_day_heat_panel.csv"),
            "--dense-panel",
            str(processed_dir / "building_day_heat_panel_dense.csv"),
            "--panel-end",
            args.date_to,
            "--output",
            str(reports_dir / "panel_quality_audit.md"),
        ],
    )
    run_step(
        "build-modeling-table",
        [
            python_executable,
            str(PROJECT_ROOT / "src" / "modeling" / "build_modeling_table.py"),
            "--input",
            str(processed_dir / "building_day_heat_panel_dense.csv"),
            "--output",
            str(processed_dir / "building_day_modeling_table.csv"),
        ],
    )

    metadata = {
        "window_name": args.window_name,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "extract_limit": args.extract_limit,
        "reference_limit": args.reference_limit,
        "batch_size": args.batch_size,
        "weather_source": weather_source,
        "weather_station_file": str(raw_dir / weather_station_filename),
        "weather_summary_file": str(processed_dir / weather_summary_filename),
        "raw_dir": str(raw_dir),
        "processed_dir": str(processed_dir),
        "reports_dir": str(reports_dir),
        "python_executable": python_executable,
    }
    metadata_path = window_root / "window_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"[window-build] metadata written to {metadata_path}", flush=True)


if __name__ == "__main__":
    main()
