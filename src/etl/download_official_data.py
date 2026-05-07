from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import urlopen

try:
    from .dataset_registry import dataset_index
except ImportError:  # pragma: no cover
    from dataset_registry import dataset_index


@dataclass(frozen=True)
class DownloadJob:
    name: str
    output_name: str
    url: str
    notes: str


def build_soda_url(dataset_id: str, *, select: str | None = None, where: str | None = None, limit: int | None = None) -> str:
    base = f"https://data.cityofnewyork.us/resource/{dataset_id}.csv"
    params: dict[str, str] = {}
    if select:
        params["$select"] = select
    if where:
        params["$where"] = where
    if limit is not None:
        params["$limit"] = str(limit)
    return base if not params else f"{base}?{urlencode(params)}"


def build_jobs(
    extract_limit: int,
    reference_limit: int,
    date_from: str | None,
    date_to: str | None,
    include_support_downloads: bool,
) -> list[DownloadJob]:
    registry = dataset_index()

    heat_where = (
        "upper(complaint_type) like '%HEAT%' "
        "or upper(descriptor) like '%HEAT%' "
        "or upper(descriptor) like '%HOT WATER%'"
    )
    hpd_problem_where = "upper(major_category) = 'HEAT/HOT WATER'"
    violation_where = (
        "upper(novdescription) like '%NO HEAT%' "
        "or upper(novdescription) like '%HOT WATER%' "
        "or upper(novdescription) like '%NO HEAT AND NO HOT WATER%'"
    )

    if date_from:
        heat_where = f"({heat_where}) and created_date >= '{date_from}T00:00:00'"
        hpd_problem_where = f"({hpd_problem_where}) and received_date >= '{date_from}T00:00:00'"
    if date_to:
        heat_where = f"({heat_where}) and created_date <= '{date_to}T23:59:59'"
        hpd_problem_where = f"({hpd_problem_where}) and received_date <= '{date_to}T23:59:59'"

    jobs = [
        DownloadJob(
            name=registry["erm2-nwe9"].name,
            output_name="nyc_311_heat_requests_filtered.csv",
            url=build_soda_url(
                "erm2-nwe9",
                select="unique_key,created_date,complaint_type,descriptor,incident_address,borough,bbl,latitude,longitude",
                where=heat_where,
                limit=extract_limit,
            ),
            notes="Filtered 311 heat/hot water starter extract.",
        ),
        DownloadJob(
            name=registry["ygpa-z7cr"].name,
            output_name="hpd_complaints_and_problems_heat.csv",
            url=build_soda_url(
                "ygpa-z7cr",
                where=hpd_problem_where,
                limit=extract_limit,
            ),
            notes="HPD complaint/problem records restricted to heat/hot water major category.",
        ),
        DownloadJob(
            name=registry["kj4p-ruqc"].name,
            output_name="hpd_buildings_sample.csv",
            url=build_soda_url("kj4p-ruqc", limit=reference_limit),
            notes="Starter building metadata sample.",
        ),
        DownloadJob(
            name=registry["tesw-yqqr"].name,
            output_name="hpd_registrations_sample.csv",
            url=build_soda_url("tesw-yqqr", limit=reference_limit),
            notes="Starter multiple dwelling registration sample.",
        ),
        DownloadJob(
            name=registry["wvxf-dwi5"].name,
            output_name="hpd_violations_heat_sample.csv",
            url=build_soda_url(
                "wvxf-dwi5",
                where=violation_where,
                limit=reference_limit,
            ),
            notes="Starter heat-related violation sample.",
        ),
        DownloadJob(
            name=registry["h4mf-f24e"].name,
            output_name="hpd_heat_sensor_program.csv",
            url=build_soda_url("h4mf-f24e", limit=reference_limit),
            notes="Heat Sensor Program reference rows.",
        ),
    ]
    if include_support_downloads:
        jobs.extend(
            [
                DownloadJob(
                    name=registry["ghcn-daily"].name,
                    output_name="noaa_ghcn_stations.txt",
                    url="https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt",
                    notes="Official NOAA station inventory.",
                ),
                DownloadJob(
                    name=registry["cre"].name,
                    output_name="census_cre_ny_state.csv",
                    url="https://api.census.gov/data/2024/cre?get=NAME,PRED0_M,PRED3_M,POPUNI&for=state:36",
                    notes="Starter CRE pull for New York state to validate API access.",
                ),
            ]
        )
    return jobs


def download_file(job: DownloadJob, output_dir: Path) -> dict[str, str | int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / job.output_name

    with urlopen(job.url, timeout=60) as response:
        content = response.read()

    output_path.write_bytes(content)

    return {
        "status": "downloaded",
        "name": job.name,
        "output_name": job.output_name,
        "path": str(output_path),
        "url": job.url,
        "bytes": len(content),
        "notes": job.notes,
    }


def write_manifest(records: Iterable[dict[str, str | int]], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"downloads": list(records)}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a day-one starter pack of official datasets for the NYC heat-risk project."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Fallback row limit used for both extract and reference pulls when specialized limits are not provided. Default: 1000",
    )
    parser.add_argument(
        "--extract-limit",
        type=int,
        default=None,
        help="Row limit for the filtered 311 and HPD complaint extracts. Defaults to --limit.",
    )
    parser.add_argument(
        "--reference-limit",
        type=int,
        default=None,
        help="Row limit for fallback/reference datasets such as building and violation samples. Defaults to --limit.",
    )
    parser.add_argument(
        "--output-dir",
        default="projects/nyc-heat-risk/data/raw",
        help="Directory where downloaded files will be written.",
    )
    parser.add_argument(
        "--manifest",
        default="projects/nyc-heat-risk/data/raw/download_manifest.json",
        help="Path for the JSON download manifest.",
    )
    parser.add_argument(
        "--date-from",
        default=None,
        help="Optional lower bound date for complaint pulls in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--date-to",
        default=None,
        help="Optional upper bound date for complaint pulls in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--skip-support-downloads",
        action="store_true",
        help="Skip slower static support downloads such as NOAA station inventory and the starter CRE pull.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    extract_limit = args.extract_limit if args.extract_limit is not None else args.limit
    reference_limit = args.reference_limit if args.reference_limit is not None else args.limit
    jobs = build_jobs(
        extract_limit=extract_limit,
        reference_limit=reference_limit,
        date_from=args.date_from,
        date_to=args.date_to,
        include_support_downloads=not args.skip_support_downloads,
    )

    output_dir = Path(args.output_dir)
    manifest_path = Path(args.manifest)

    results = []
    for job in jobs:
        try:
            result = download_file(job, output_dir=output_dir)
            results.append(result)
            print(f"downloaded {job.output_name} ({result['bytes']} bytes)", flush=True)
        except Exception as exc:
            results.append(
                {
                    "status": "failed",
                    "name": job.name,
                    "output_name": job.output_name,
                    "path": str(output_dir / job.output_name),
                    "url": job.url,
                    "bytes": 0,
                    "notes": job.notes,
                    "error": str(exc),
                }
            )
            print(f"failed {job.output_name}: {exc}", flush=True)

    write_manifest(results, manifest_path)
    print(f"manifest written to {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
