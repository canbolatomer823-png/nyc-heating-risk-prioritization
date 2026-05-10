from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


@dataclass(frozen=True)
class LinkedDataset:
    name: str
    dataset_id: str
    building_id_field: str
    output_name: str
    select: str | None = None


LINKED_DATASETS = [
    LinkedDataset(
        name="HPD Buildings linked to complaint buildings",
        dataset_id="kj4p-ruqc",
        building_id_field="buildingid",
        output_name="hpd_buildings_linked.csv",
    ),
    LinkedDataset(
        name="HPD Registrations linked to complaint buildings",
        dataset_id="tesw-yqqr",
        building_id_field="buildingid",
        output_name="hpd_registrations_linked.csv",
    ),
    LinkedDataset(
        name="HPD Violations linked to complaint buildings",
        dataset_id="wvxf-dwi5",
        building_id_field="buildingid",
        output_name="hpd_violations_linked.csv",
    ),
]


def read_complaint_building_ids(complaints_path: Path) -> list[str]:
    building_ids: set[str] = set()
    with complaints_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            building_id = (row.get("building_id") or "").strip()
            if building_id:
                building_ids.add(building_id)
    return sorted(building_ids)


def build_in_clause(field: str, values: list[str]) -> str:
    quoted = ",".join(f"'{value}'" for value in values)
    return f"{field} in({quoted})"


def build_url(dataset: LinkedDataset, building_ids: list[str]) -> str:
    params: dict[str, str] = {"$where": build_in_clause(dataset.building_id_field, building_ids)}
    if dataset.select:
        params["$select"] = dataset.select
    return f"https://data.cityofnewyork.us/resource/{dataset.dataset_id}.csv?{urlencode(params)}"


def download_text(url: str) -> bytes:
    with urlopen(url, timeout=60) as response:
        return response.read()


def download_batch_with_retry(
    dataset: LinkedDataset,
    building_ids: list[str],
    retries: int = 5,
    backoff_seconds: float = 1.5,
) -> bytes:
    url = build_url(dataset, building_ids)
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return download_text(url)
        except (HTTPError, URLError, TimeoutError, ConnectionResetError, OSError) as error:
            last_error = error
            if attempt < retries - 1:
                time.sleep(backoff_seconds * (attempt + 1))
                continue
            break

    if len(building_ids) > 1:
        midpoint = max(1, len(building_ids) // 2)
        left = download_batch_with_retry(dataset, building_ids[:midpoint], retries=retries)
        right = download_batch_with_retry(dataset, building_ids[midpoint:], retries=retries)
        right_lines = right.splitlines()
        if left and len(right_lines) > 1:
            return left + b"\n" + b"\n".join(right_lines[1:])
        if left:
            return left
        return right

    if last_error is not None:
        raise last_error
    raise RuntimeError("Linked dataset download failed without a captured exception.")


def write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def chunked(values: list[str], size: int):
    iterator = iter(values)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            break
        yield batch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download HPD rows that are directly linked to the complaint building ids in the starter extract."
    )
    parser.add_argument(
        "--complaints-path",
        default="projects/nyc-heat-risk/data/raw/hpd_complaints_and_problems_heat.csv",
        help="CSV path for the filtered HPD complaints and problems extract.",
    )
    parser.add_argument(
        "--output-dir",
        default="projects/nyc-heat-risk/data/raw",
        help="Directory where linked HPD CSV files will be written.",
    )
    parser.add_argument(
        "--manifest",
        default="projects/nyc-heat-risk/data/raw/linked_download_manifest.json",
        help="Manifest path for linked dataset downloads.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=150,
        help="Maximum number of building ids per Socrata request.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    complaints_path = Path(args.complaints_path)
    output_dir = Path(args.output_dir)
    manifest_path = Path(args.manifest)

    building_ids = read_complaint_building_ids(complaints_path)
    if not building_ids:
        raise SystemExit("No building_id values were found in the complaints file.")

    results = []
    for dataset in LINKED_DATASETS:
        output_path = output_dir / dataset.output_name
        combined_content: bytes | None = None
        batch_count = 0

        for batch in chunked(building_ids, args.batch_size):
            content = download_batch_with_retry(dataset, batch)
            lines = content.splitlines()
            if combined_content is None:
                combined_content = content
            elif len(lines) > 1:
                combined_content += b"\n" + b"\n".join(lines[1:])
            batch_count += 1
            if batch_count % 20 == 0:
                print(
                    f"{dataset.output_name}: completed {batch_count} batches",
                    flush=True,
                )

        combined_content = combined_content or b""
        write_bytes(output_path, combined_content)
        record = {
            "name": dataset.name,
            "dataset_id": dataset.dataset_id,
            "path": str(output_path),
            "building_id_count": len(building_ids),
            "bytes": len(combined_content),
            "batch_count": batch_count,
        }
        results.append(record)
        print(f"downloaded {dataset.output_name} ({len(combined_content)} bytes across {batch_count} batches)", flush=True)

    manifest_path.write_text(json.dumps({"downloads": results}, indent=2), encoding="utf-8")
    print(f"manifest written to {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
