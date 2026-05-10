from __future__ import annotations

import argparse
import csv
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path


def parse_date(value: str | None) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def safe_int(value: str | int | None) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def read_csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def add_sample(samples: list[str], sample: str, limit: int = 5) -> None:
    if len(samples) < limit:
        samples.append(sample)


@dataclass
class SparseAudit:
    row_count: int = 0
    building_ids: set[str] = field(default_factory=set)
    dates: set[date] = field(default_factory=set)
    duplicate_pairs: int = 0
    seen_pairs: set[tuple[str, date]] = field(default_factory=set)
    missing_building_metadata: int = 0
    missing_census_tract: int = 0
    missing_bbl: int = 0
    future_violation_dates: int = 0
    negative_violation_counts: int = 0
    total_violation_decreases: int = 0
    open_violation_decreases_below_zero: int = 0
    top_boroughs: Counter[str] = field(default_factory=Counter)
    samples: dict[str, list[str]] = field(default_factory=lambda: {
        "duplicate_pairs": [],
        "future_violation_dates": [],
        "total_violation_decreases": [],
        "missing_metadata": [],
    })


@dataclass
class DenseAudit:
    row_count: int = 0
    building_ids: set[str] = field(default_factory=set)
    dates: set[date] = field(default_factory=set)
    duplicate_pairs: int = 0
    unsorted_pairs: int = 0
    weather_missing_rows: int = 0
    cre_missing_rows: int = 0
    cre_missing_on_nonempty_tract_rows: int = 0
    asof_future_rows: int = 0
    latest_violation_future_rows: int = 0
    pre_snapshot_nonzero_violation_rows: int = 0
    complaint_without_snapshot_rows: int = 0
    target_mismatch_rows: int = 0
    lag_mismatch_rows: int = 0
    rolling_mismatch_rows: int = 0
    cumulative_mismatch_rows: int = 0
    prior_max_mismatch_rows: int = 0
    days_since_mismatch_rows: int = 0
    invalid_label_rows: int = 0
    samples: dict[str, list[str]] = field(default_factory=lambda: {
        "cre_missing_on_nonempty_tract_rows": [],
        "asof_future_rows": [],
        "latest_violation_future_rows": [],
        "pre_snapshot_nonzero_violation_rows": [],
        "target_mismatch_rows": [],
        "lag_mismatch_rows": [],
        "rolling_mismatch_rows": [],
        "cumulative_mismatch_rows": [],
        "days_since_mismatch_rows": [],
        "invalid_label_rows": [],
    })


def audit_sparse(path: Path) -> SparseAudit:
    audit = SparseAudit()
    last_total_by_building: dict[str, int] = {}
    last_date_by_building: dict[str, date] = {}

    for row in read_csv_rows(path):
        audit.row_count += 1
        building_id = (row.get("building_id") or "").strip()
        complaint_date = parse_date(row.get("complaint_date"))
        if not building_id or complaint_date is None:
            continue

        audit.building_ids.add(building_id)
        audit.dates.add(complaint_date)
        audit.top_boroughs[(row.get("borough") or "UNKNOWN").strip() or "UNKNOWN"] += 1

        pair = (building_id, complaint_date)
        if pair in audit.seen_pairs:
            audit.duplicate_pairs += 1
            add_sample(audit.samples["duplicate_pairs"], f"{building_id}|{complaint_date}")
        audit.seen_pairs.add(pair)

        if not (row.get("management_program") or "").strip():
            audit.missing_building_metadata += 1
            add_sample(audit.samples["missing_metadata"], f"{building_id}|{complaint_date}")
        if not (row.get("census_tract") or "").strip():
            audit.missing_census_tract += 1
        if not (row.get("building_bbl") or "").strip():
            audit.missing_bbl += 1

        latest_violation_date = parse_date(row.get("latest_linked_violation_date"))
        if latest_violation_date is not None and latest_violation_date > complaint_date:
            audit.future_violation_dates += 1
            add_sample(
                audit.samples["future_violation_dates"],
                f"{building_id}|complaint={complaint_date}|latest_violation={latest_violation_date}",
            )

        total_violations = safe_int(row.get("total_linked_violation_count"))
        open_violations = safe_int(row.get("open_linked_violation_count"))
        if total_violations < 0 or open_violations < 0:
            audit.negative_violation_counts += 1

        previous_total = last_total_by_building.get(building_id)
        previous_date = last_date_by_building.get(building_id)
        if previous_total is not None and previous_date is not None and complaint_date >= previous_date:
            if total_violations < previous_total:
                audit.total_violation_decreases += 1
                add_sample(
                    audit.samples["total_violation_decreases"],
                    f"{building_id}|{previous_date}->{complaint_date}|{previous_total}->{total_violations}",
                )
        last_total_by_building[building_id] = total_violations
        last_date_by_building[building_id] = complaint_date

    return audit


def audit_dense(path: Path, panel_end: date | None) -> DenseAudit:
    audit = DenseAudit()
    previous_pair: tuple[str, date] | None = None
    current_building = ""
    rolling_counts: deque[int] = deque(maxlen=7)
    rolling_requests: deque[int] = deque(maxlen=7)
    cumulative_complaints = 0
    cumulative_requests = 0
    complaint_day_count_prior = 0
    prior_max_daily_complaints = 0
    previous_complaint_date: date | None = None
    previous_row: dict[str, str] | None = None
    previous_date: date | None = None

    for row in read_csv_rows(path):
        audit.row_count += 1
        building_id = (row.get("building_id") or "").strip()
        current_date = parse_date(row.get("calendar_date"))
        if not building_id or current_date is None:
            continue

        pair = (building_id, current_date)
        if previous_pair == pair:
            audit.duplicate_pairs += 1
        if previous_pair is not None and pair < previous_pair:
            audit.unsorted_pairs += 1
        previous_pair = pair

        if building_id != current_building:
            current_building = building_id
            rolling_counts.clear()
            rolling_requests.clear()
            cumulative_complaints = 0
            cumulative_requests = 0
            complaint_day_count_prior = 0
            prior_max_daily_complaints = 0
            previous_complaint_date = None
            previous_row = None
            previous_date = None

        audit.building_ids.add(building_id)
        audit.dates.add(current_date)

        complaint_count = safe_int(row.get("complaint_count"))
        unique_request_count = safe_int(row.get("unique_request_count"))

        if previous_row is not None and previous_date is not None:
            expected_next_date = previous_date + timedelta(days=1)
            if current_date == expected_next_date:
                expected_next_count = complaint_count
                expected_surge = 1 if complaint_count >= 1 else 0
                if safe_int(previous_row.get("next_day_complaint_count")) != expected_next_count:
                    audit.target_mismatch_rows += 1
                    add_sample(
                        audit.samples["target_mismatch_rows"],
                        f"{building_id}|{previous_date}|expected_next={expected_next_count}",
                    )
                if safe_int(previous_row.get("surge_flag")) != expected_surge:
                    audit.target_mismatch_rows += 1

        if safe_int(row.get("weather_station_count")) <= 0:
            audit.weather_missing_rows += 1
        if safe_int(row.get("cre_coverage_flag")) <= 0:
            audit.cre_missing_rows += 1
            if (row.get("census_tract") or "").strip():
                audit.cre_missing_on_nonempty_tract_rows += 1
                add_sample(audit.samples["cre_missing_on_nonempty_tract_rows"], f"{building_id}|{current_date}|tract={(row.get('census_tract') or '').strip()}")

        asof_date = parse_date(row.get("as_of_source_date"))
        if asof_date is not None and asof_date > current_date:
            audit.asof_future_rows += 1
            add_sample(audit.samples["asof_future_rows"], f"{building_id}|{current_date}|asof={asof_date}")

        latest_violation_date = parse_date(row.get("latest_linked_violation_date"))
        if latest_violation_date is not None and latest_violation_date > current_date:
            audit.latest_violation_future_rows += 1
            add_sample(
                audit.samples["latest_violation_future_rows"],
                f"{building_id}|{current_date}|latest_violation={latest_violation_date}",
            )

        snapshot_available = safe_int(row.get("as_of_snapshot_available_flag"))
        if snapshot_available == 0 and (
            safe_int(row.get("total_linked_violation_count")) > 0
            or safe_int(row.get("open_linked_violation_count")) > 0
        ):
            audit.pre_snapshot_nonzero_violation_rows += 1
            add_sample(audit.samples["pre_snapshot_nonzero_violation_rows"], f"{building_id}|{current_date}")
        if complaint_count > 0 and snapshot_available == 0:
            audit.complaint_without_snapshot_rows += 1

        if safe_int(row.get("lag_1_complaints")) != (rolling_counts[-1] if rolling_counts else 0):
            audit.lag_mismatch_rows += 1
            add_sample(audit.samples["lag_mismatch_rows"], f"{building_id}|{current_date}")

        expected_rolling_counts = list(rolling_counts) + [complaint_count]
        expected_rolling_requests = list(rolling_requests) + [unique_request_count]
        expected_rolling_3 = sum(expected_rolling_counts[-3:])
        expected_rolling_7 = sum(expected_rolling_counts[-7:])
        expected_rolling_7_requests = sum(expected_rolling_requests[-7:])
        if (
            safe_int(row.get("rolling_3d_complaints")) != expected_rolling_3
            or safe_int(row.get("rolling_7d_complaints")) != expected_rolling_7
            or safe_int(row.get("rolling_7d_request_count")) != expected_rolling_7_requests
        ):
            audit.rolling_mismatch_rows += 1
            add_sample(audit.samples["rolling_mismatch_rows"], f"{building_id}|{current_date}")

        if (
            safe_int(row.get("complaint_day_count_prior")) != complaint_day_count_prior
            or safe_int(row.get("cumulative_complaints_prior")) != cumulative_complaints
            or safe_int(row.get("cumulative_request_count_prior")) != cumulative_requests
        ):
            audit.cumulative_mismatch_rows += 1
            add_sample(audit.samples["cumulative_mismatch_rows"], f"{building_id}|{current_date}")

        if safe_int(row.get("prior_max_daily_complaints")) != prior_max_daily_complaints:
            audit.prior_max_mismatch_rows += 1
            add_sample(audit.samples["cumulative_mismatch_rows"], f"{building_id}|{current_date}|prior_max")

        expected_days_since = (current_date - previous_complaint_date).days if previous_complaint_date else -1
        if safe_int(row.get("days_since_last_complaint")) != expected_days_since:
            audit.days_since_mismatch_rows += 1
            add_sample(audit.samples["days_since_mismatch_rows"], f"{building_id}|{current_date}")

        if panel_end is not None:
            expected_label_available = 1 if current_date < panel_end else 0
            if safe_int(row.get("next_day_label_available")) != expected_label_available:
                audit.invalid_label_rows += 1
                add_sample(audit.samples["invalid_label_rows"], f"{building_id}|{current_date}")

        rolling_counts.append(complaint_count)
        rolling_requests.append(unique_request_count)
        cumulative_complaints += complaint_count
        cumulative_requests += unique_request_count
        if complaint_count > 0:
            complaint_day_count_prior += 1
            prior_max_daily_complaints = max(prior_max_daily_complaints, complaint_count)
            previous_complaint_date = current_date
        previous_row = row
        previous_date = current_date

    return audit


def percent(part: int, whole: int) -> str:
    if whole == 0:
        return "n/a"
    return f"{part / whole:.4%}"


def sample_lines(title: str, samples: list[str]) -> list[str]:
    if not samples:
        return [f"- {title}: none"]
    lines = [f"- {title}: {len(samples)} sample(s)"]
    for sample in samples:
        lines.append(f"  - `{sample}`")
    return lines


def write_report(sparse: SparseAudit, dense: DenseAudit, output_path: Path) -> None:
    sparse_start = min(sparse.dates).isoformat() if sparse.dates else "n/a"
    sparse_end = max(sparse.dates).isoformat() if sparse.dates else "n/a"
    dense_start = min(dense.dates).isoformat() if dense.dates else "n/a"
    dense_end = max(dense.dates).isoformat() if dense.dates else "n/a"

    lines = [
        "# Panel Quality Audit",
        "",
        "## Sparse Complaint Panel",
        f"- Rows: {sparse.row_count}",
        f"- Unique buildings: {len(sparse.building_ids)}",
        f"- Date range: {sparse_start} -> {sparse_end}",
        f"- Duplicate building-date rows: {sparse.duplicate_pairs}",
        f"- Rows missing linked building metadata: {sparse.missing_building_metadata} ({percent(sparse.missing_building_metadata, sparse.row_count)})",
        f"- Rows missing census tract: {sparse.missing_census_tract} ({percent(sparse.missing_census_tract, sparse.row_count)})",
        f"- Rows missing BBL: {sparse.missing_bbl} ({percent(sparse.missing_bbl, sparse.row_count)})",
        f"- Future-dated latest violation rows: {sparse.future_violation_dates}",
        f"- Negative violation count rows: {sparse.negative_violation_counts}",
        f"- Total violation count decreases within building: {sparse.total_violation_decreases}",
        "",
        "### Sparse Borough Distribution",
    ]
    for borough, count in sparse.top_boroughs.most_common():
        lines.append(f"- {borough}: {count}")

    lines.extend(
        [
            "",
            "## Dense Building-Day Panel",
            f"- Rows: {dense.row_count}",
            f"- Unique buildings: {len(dense.building_ids)}",
            f"- Date range: {dense_start} -> {dense_end}",
            f"- Duplicate adjacent building-date rows: {dense.duplicate_pairs}",
            f"- Unsorted adjacent building-date rows: {dense.unsorted_pairs}",
            f"- Weather missing rows: {dense.weather_missing_rows}",
            f"- CRE missing rows: {dense.cre_missing_rows}",
            f"- CRE missing rows with nonempty tract: {dense.cre_missing_on_nonempty_tract_rows}",
            f"- Future as-of source rows: {dense.asof_future_rows}",
            f"- Future latest violation rows: {dense.latest_violation_future_rows}",
            f"- Pre-snapshot rows with nonzero violation features: {dense.pre_snapshot_nonzero_violation_rows}",
            f"- Complaint rows without as-of snapshot: {dense.complaint_without_snapshot_rows}",
            f"- Next-day target mismatches: {dense.target_mismatch_rows}",
            f"- Lag mismatches: {dense.lag_mismatch_rows}",
            f"- Rolling-window mismatches: {dense.rolling_mismatch_rows}",
            f"- Cumulative-feature mismatches: {dense.cumulative_mismatch_rows}",
            f"- Prior-max mismatches: {dense.prior_max_mismatch_rows}",
            f"- Days-since-last-complaint mismatches: {dense.days_since_mismatch_rows}",
            f"- Label availability mismatches: {dense.invalid_label_rows}",
            "",
            "## Sample Findings",
        ]
    )
    for key, samples in {**sparse.samples, **dense.samples}.items():
        lines.extend(sample_lines(key, samples))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit sparse and dense NYC heating panel quality.")
    parser.add_argument("--sparse-panel", required=True, help="Sparse building-day panel CSV path.")
    parser.add_argument("--dense-panel", required=True, help="Dense building-day panel CSV path.")
    parser.add_argument("--panel-end", default=None, help="Expected inclusive panel end date in YYYY-MM-DD format.")
    parser.add_argument("--output", required=True, help="Markdown quality audit report path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sparse = audit_sparse(Path(args.sparse_panel))
    dense = audit_dense(Path(args.dense_panel), panel_end=parse_date(args.panel_end))
    write_report(sparse, dense, Path(args.output))
    print(f"wrote panel quality audit to {args.output}", flush=True)


if __name__ == "__main__":
    main()
