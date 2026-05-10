from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


BOROUGH_TO_COUNTY = {
    "BRONX": "005",
    "BROOKLYN": "047",
    "MANHATTAN": "061",
    "QUEENS": "081",
    "STATEN ISLAND": "085",
}

COUNTY_TO_BOROUGH = {value: key for key, value in BOROUGH_TO_COUNTY.items()}
STATE_FIPS = "36"
CRE_FIELDS = ["NAME", "GEO_ID", "POPUNI", "PRED0_PE", "PRED3_PE", "PRED12_PE"]


def build_url(county_fips: str) -> str:
    params = {
        "get": ",".join(CRE_FIELDS),
        "for": "tract:*",
        "in": f"state:{STATE_FIPS} county:{county_fips}",
    }
    return f"https://api.census.gov/data/2024/cre?{urlencode(params)}"


def normalize_tract_code(value: str) -> str:
    digits = "".join(ch for ch in (value or "").strip() if ch.isdigit())
    return digits.zfill(6) if digits else ""


def download_county_rows(county_fips: str) -> list[dict[str, str]]:
    with urlopen(build_url(county_fips), timeout=60) as response:
        rows = json.loads(response.read().decode("utf-8"))
    header, values = rows[0], rows[1:]
    borough = COUNTY_TO_BOROUGH[county_fips]
    output_rows: list[dict[str, str]] = []
    for value_row in values:
        row = dict(zip(header, value_row))
        row["borough"] = borough
        row["county_fips"] = county_fips
        row["tract_code"] = normalize_tract_code(row.get("tract", ""))
        output_rows.append(row)
    return output_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = [
        "borough",
        "county_fips",
        "state",
        "county",
        "tract",
        "tract_code",
        "GEO_ID",
        "NAME",
        "POPUNI",
        "PRED0_PE",
        "PRED3_PE",
        "PRED12_PE",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download official 2024 Census CRE tract-level data for NYC boroughs.")
    parser.add_argument(
        "--output",
        default="projects/nyc-heat-risk/data/raw/census_cre_nyc_tract_2024.csv",
        help="CSV output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, str]] = []
    for county_fips in sorted(COUNTY_TO_BOROUGH):
        rows.extend(download_county_rows(county_fips))
    output_path = Path(args.output)
    write_csv(output_path, rows)
    print(f"wrote {len(rows)} CRE tract rows to {output_path}", flush=True)


if __name__ == "__main__":
    main()
