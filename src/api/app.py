from __future__ import annotations

import os
import sqlite3
from html import escape
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, validator

from aws.artifact_store import derive_s3_key, download_s3_object, head_s3_object
from modeling.feature_explanations import explain_model_rows
from modeling.risk_features import MODEL_INPUT_COLUMNS, NUMERIC_FEATURES, prepare_feature_frame
from project_paths import FINAL_MODEL_BUNDLE_PATH, FINAL_PRIORITY_CSV_PATH, FINAL_RECORD_LOOKUP_DB_PATH, FINAL_SCORED_CSV_PATH


MODEL_BUNDLE_PATH = Path(os.getenv("NYC_HEAT_MODEL_BUNDLE", str(FINAL_MODEL_BUNDLE_PATH)))
PRIORITY_CSV_PATH = Path(os.getenv("NYC_HEAT_PRIORITY_CSV", str(FINAL_PRIORITY_CSV_PATH)))
RECORD_LOOKUP_DB_PATH = Path(os.getenv("NYC_HEAT_RECORD_LOOKUP_DB", str(FINAL_RECORD_LOOKUP_DB_PATH)))
SCORED_CSV_PATH = Path(
    os.getenv("NYC_HEAT_SCORED_CSV", str(FINAL_SCORED_CSV_PATH))
)
S3_BUCKET = os.getenv("NYC_HEAT_S3_BUCKET")
S3_PREFIX = os.getenv("NYC_HEAT_S3_PREFIX", "").strip("/")
S3_MODEL_KEY = os.getenv("NYC_HEAT_S3_MODEL_KEY") or derive_s3_key(S3_PREFIX, "models/logistic_regression_bundle.joblib")
S3_PRIORITY_KEY = os.getenv("NYC_HEAT_S3_PRIORITY_KEY") or derive_s3_key(S3_PREFIX, "priority/inspection_priority_latest_day.csv")
S3_RECORD_LOOKUP_KEY = os.getenv("NYC_HEAT_S3_RECORD_LOOKUP_KEY") or derive_s3_key(S3_PREFIX, "lookup/record_lookup.sqlite")
S3_SCORED_KEY = os.getenv("NYC_HEAT_S3_SCORED_KEY") or derive_s3_key(S3_PREFIX, "scored/logistic_regression_scored.csv")
LOCAL_CACHE_DIR = Path(os.getenv("NYC_HEAT_LOCAL_CACHE_DIR", "/tmp/nyc-heat-risk"))
AWS_REGION = os.getenv("AWS_REGION")

PRIORITY_COLUMNS = [
    "calendar_date",
    "building_id",
    "building_bbl",
    "borough",
    "incident_address",
    "model_probability",
    "model_prediction",
    "model_threshold",
    "open_linked_violation_count",
    "cumulative_complaints_prior",
    "heat_sensor_active_flag",
    "management_program",
]

PRIORITY_NUMERIC_COLUMNS = [
    "model_probability",
    "model_prediction",
    "model_threshold",
    "open_linked_violation_count",
    "cumulative_complaints_prior",
    "heat_sensor_active_flag",
    "inspection_priority_rank",
]

STRING_COLUMNS = [
    "calendar_date",
    "building_id",
    "building_bbl",
    "borough",
    "incident_address",
    "management_program",
]


class ScoreRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., description="Pre-engineered building-day feature rows.")

    @validator("rows")
    @classmethod
    def validate_row_count(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(v) < 1 or len(v) > 500:
            raise ValueError(f"Rows must be between 1 and 500, got {len(v)}")
        return v


class ScoreResponseRow(BaseModel):
    probability: float
    threshold: float
    prediction: int
    why_risky: str
    top_positive_contributors: list[dict[str, Any]]
    top_negative_contributors: list[dict[str, Any]]


app = FastAPI(
    title="NYC Heating and Hot Water Complaint Risk API",
    version="0.1.0",
    description="Score next-day building-level heat/hot water complaint risk and serve inspection priorities.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _preload_artifacts() -> None:
    _ = load_bundle()
    try:
        _ = load_priority_frame()
    except Exception:
        pass
    record_lookup_db_is_available()


def artifact_source() -> dict[str, Any]:
    if S3_BUCKET:
        return {
            "type": "s3",
            "bucket": S3_BUCKET,
            "model_key": S3_MODEL_KEY,
            "priority_key": S3_PRIORITY_KEY,
            "record_lookup_key": S3_RECORD_LOOKUP_KEY,
            "scored_key": S3_SCORED_KEY,
            "cache_dir": str(LOCAL_CACHE_DIR),
        }
    return {
        "type": "local",
        "model_path": str(MODEL_BUNDLE_PATH),
        "priority_path": str(PRIORITY_CSV_PATH),
        "record_lookup_path": str(RECORD_LOOKUP_DB_PATH),
        "scored_path": str(SCORED_CSV_PATH),
    }


def resolve_model_bundle_path() -> Path:
    if S3_BUCKET:
        return download_s3_object(
            bucket=S3_BUCKET,
            key=S3_MODEL_KEY,
            destination=LOCAL_CACHE_DIR / "models" / "logistic_regression_bundle.joblib",
            region_name=AWS_REGION,
        )
    return MODEL_BUNDLE_PATH


def resolve_scored_csv_path() -> Path:
    if S3_BUCKET:
        return download_s3_object(
            bucket=S3_BUCKET,
            key=S3_SCORED_KEY,
            destination=LOCAL_CACHE_DIR / "scored" / "logistic_regression_scored.csv",
            region_name=AWS_REGION,
        )
    return SCORED_CSV_PATH


def resolve_record_lookup_db_path() -> Path:
    if S3_BUCKET:
        return download_s3_object(
            bucket=S3_BUCKET,
            key=S3_RECORD_LOOKUP_KEY,
            destination=LOCAL_CACHE_DIR / "lookup" / "record_lookup.sqlite",
            region_name=AWS_REGION,
        )
    return RECORD_LOOKUP_DB_PATH


def resolve_priority_csv_path() -> Path:
    if S3_BUCKET:
        return download_s3_object(
            bucket=S3_BUCKET,
            key=S3_PRIORITY_KEY,
            destination=LOCAL_CACHE_DIR / "priority" / "inspection_priority_latest_day.csv",
            region_name=AWS_REGION,
        )
    return PRIORITY_CSV_PATH


@lru_cache(maxsize=1)
def load_bundle() -> dict[str, Any]:
    bundle_path = resolve_model_bundle_path()
    _validate_model_path(bundle_path)
    bundle = joblib.load(bundle_path)
    if "model" not in bundle or "metadata" not in bundle:
        raise RuntimeError("Model bundle is missing required keys.")
    return bundle


_ALLOWED_DATA_ROOTS = [
    Path(__file__).resolve().parents[2] / "data",
    Path("/tmp/nyc-heat-risk"),
]


def _validate_model_path(path: Path) -> None:
    resolved = path.resolve()
    if resolved.is_symlink():
        raise ValueError(f"Refusing to load model via symlink: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"Model path is not a regular file: {resolved}")
    for root in _ALLOWED_DATA_ROOTS:
        if str(resolved).startswith(str(root.resolve()) + os.sep) or resolved == root.resolve():
            return
    raise ValueError(f"Model path outside allowed directories: {resolved}")


def normalize_priority_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in STRING_COLUMNS:
        if column in normalized.columns:
            normalized[column] = normalized[column].fillna("").astype(str)
    for column in PRIORITY_NUMERIC_COLUMNS:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce").fillna(0)
    if "model_prediction" in normalized.columns:
        normalized["model_prediction"] = normalized["model_prediction"].astype(int)
    if "inspection_priority_rank" in normalized.columns:
        normalized["inspection_priority_rank"] = normalized["inspection_priority_rank"].astype(int)
    return normalized


@lru_cache(maxsize=1)
def load_priority_frame() -> pd.DataFrame:
    priority_path = resolve_priority_csv_path()
    if not priority_path.exists():
        raise RuntimeError(f"Missing priority CSV: {priority_path}")
    frame = pd.read_csv(priority_path, low_memory=False)
    return normalize_priority_frame(frame)


def model_components() -> tuple[Any, dict[str, Any]]:
    bundle = load_bundle()
    return bundle["model"], bundle.get("calibrator"), bundle["metadata"]


def scored_row_count_from_metadata(metadata: dict[str, Any]) -> int:
    metrics = metadata.get("metrics", {})
    return int(sum(int(split_metrics.get("rows", 0)) for split_metrics in metrics.values()))


def latest_priority_date_from_metadata(metadata: dict[str, Any]) -> str:
    ranking_metrics = metadata.get("ranking_metrics", {})
    for key in ("50", "25", "10", "100"):
        latest = ranking_metrics.get(key, {}).get("latest_date")
        if latest:
            return str(latest)
    return "n/a"


def scored_csv_is_available() -> bool:
    if S3_BUCKET:
        return head_s3_object(S3_BUCKET, S3_SCORED_KEY, region_name=AWS_REGION) is not None
    return resolve_scored_csv_path().exists()


def scored_csv_is_readable() -> bool:
    try:
        if S3_BUCKET:
            metadata = head_s3_object(S3_BUCKET, S3_SCORED_KEY, region_name=AWS_REGION)
            return metadata is not None and int(metadata.get("ContentLength", 0)) > 0
        scored_path = resolve_scored_csv_path()
        if not scored_path.exists():
            return False
        pd.read_csv(scored_path, usecols=PRIORITY_COLUMNS, nrows=1, low_memory=False)
        return True
    except Exception:
        return False


def record_lookup_db_is_available() -> bool:
    if S3_BUCKET:
        return head_s3_object(S3_BUCKET, S3_RECORD_LOOKUP_KEY, region_name=AWS_REGION) is not None
    return resolve_record_lookup_db_path().exists()


def find_record_in_lookup_db(building_id: str, calendar_date: str) -> dict[str, Any] | None:
    lookup_path = resolve_record_lookup_db_path()
    if not lookup_path.exists():
        return None

    query = """
        SELECT
            calendar_date,
            building_id,
            building_bbl,
            borough,
            incident_address,
            model_probability,
            model_prediction,
            model_threshold,
            open_linked_violation_count,
            cumulative_complaints_prior,
            heat_sensor_active_flag,
            management_program
        FROM record_lookup
        WHERE building_id = ? AND calendar_date = ?
        ORDER BY model_probability DESC
        LIMIT 1
    """
    with sqlite3.connect(lookup_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(query, (str(building_id), str(calendar_date))).fetchone()
    return dict(row) if row is not None else None


def find_record_in_scored_csv(building_id: str, calendar_date: str) -> dict[str, Any] | None:
    scored_path = resolve_scored_csv_path()
    if not scored_path.exists():
        raise RuntimeError(f"Missing scored CSV: {scored_path}")

    dtype_map = {column: "string" for column in STRING_COLUMNS if column in PRIORITY_COLUMNS}
    for chunk in pd.read_csv(scored_path, usecols=PRIORITY_COLUMNS, chunksize=100_000, dtype=dtype_map):
        normalized = normalize_priority_frame(chunk)
        matches = normalized[
            (normalized["building_id"] == str(building_id)) & (normalized["calendar_date"] == str(calendar_date))
        ]
        if not matches.empty:
            row = matches.sort_values("model_probability", ascending=False).iloc[0].to_dict()
            return row
    return None


def logit_feature(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def apply_calibration(calibrator: Any, probabilities: np.ndarray) -> np.ndarray:
    if calibrator is None:
        return np.asarray(probabilities, dtype=float)
    return calibrator.predict_proba(logit_feature(np.asarray(probabilities, dtype=float)))[:, 1]


def to_jsonable_record(row: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in row.items():
        if pd.isna(value):
            cleaned[key] = None
        elif hasattr(value, "item"):
            cleaned[key] = value.item()
        else:
            cleaned[key] = value
    return cleaned


def dashboard_value(value: Any, digits: int = 3) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_dashboard_html(frame: pd.DataFrame, top_n: int, borough_filter: Optional[str], metadata: dict[str, Any]) -> str:
    if frame.empty:
        raise HTTPException(status_code=404, detail="No priority rows available.")

    ranked = frame.sort_values(
        "inspection_priority_rank" if "inspection_priority_rank" in frame.columns else "model_probability",
        ascending=True if "inspection_priority_rank" in frame.columns else False,
    ).copy()
    boroughs = sorted(
        str(value)
        for value in ranked.get("borough", pd.Series(dtype=str)).dropna().unique()
        if str(value).strip()
    )
    active_borough = (borough_filter or "").strip().upper()
    if active_borough and active_borough != "ALL" and "borough" in ranked.columns:
        ranked = ranked[ranked["borough"].astype(str).str.upper() == active_borough]

    rows = ranked.head(top_n)
    latest_date = str(frame["calendar_date"].iloc[0]) if "calendar_date" in frame.columns else latest_priority_date_from_metadata(metadata)
    test_metrics = metadata.get("metrics", {}).get("test", {})
    ranking_50 = metadata.get("ranking_metrics", {}).get("50", {})
    avg_probability = float(rows["model_probability"].mean()) if "model_probability" in rows and not rows.empty else 0.0
    max_probability = float(rows["model_probability"].max()) if "model_probability" in rows and not rows.empty else 0.0

    borough_options = ['<option value="ALL">All boroughs</option>']
    for borough in boroughs:
        selected = " selected" if borough.upper() == active_borough else ""
        borough_options.append(f'<option value="{escape(borough)}"{selected}>{escape(borough)}</option>')

    row_html: list[str] = []
    for row in rows.to_dict(orient="records"):
        rank = dashboard_value(row.get("inspection_priority_rank"), digits=0)
        probability = dashboard_value(float(row.get("model_probability", 0)) * 100, digits=1)
        equity_score = dashboard_value(row.get("equity_weighted_priority_score"), digits=3)
        why_risky = dashboard_value(row.get("why_risky"))
        row_html.append(
            "<tr>"
            f"<td class='rank'>{escape(rank)}</td>"
            f"<td><strong>{escape(dashboard_value(row.get('building_id')))}</strong><br>"
            f"<span>{escape(dashboard_value(row.get('incident_address')))}</span></td>"
            f"<td>{escape(dashboard_value(row.get('borough')))}</td>"
            f"<td>{probability}%</td>"
            f"<td>{escape(equity_score)}</td>"
            f"<td>{escape(dashboard_value(row.get('open_linked_violation_count'), digits=0))}</td>"
            f"<td>{escape(dashboard_value(row.get('cumulative_complaints_prior'), digits=0))}</td>"
            f"<td class='why'>{escape(why_risky)}</td>"
            "</tr>"
        )

    if not row_html:
        row_html.append("<tr><td colspan='8'>No rows match this filter.</td></tr>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NYC Heating Risk Dashboard</title>
  <style>
    :root {{
      --ink: #16202a;
      --muted: #607080;
      --panel: #ffffff;
      --line: #d8e0e7;
      --warm: #d95d39;
      --cold: #1f6f8b;
      --bg: #f3f0e8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(217, 93, 57, .22), transparent 30%),
        linear-gradient(135deg, #f7f2e8 0%, #e8f0f3 100%);
      font-family: Georgia, "Times New Roman", serif;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 34px 22px 48px; }}
    .hero {{
      border: 1px solid rgba(22, 32, 42, .12);
      background: rgba(255, 255, 255, .82);
      border-radius: 28px;
      padding: 30px;
      box-shadow: 0 22px 55px rgba(22, 32, 42, .08);
    }}
    h1 {{ margin: 0; max-width: 880px; font-size: clamp(2.1rem, 5vw, 4.6rem); line-height: .96; }}
    .subtitle {{ max-width: 790px; color: var(--muted); font-size: 1.08rem; line-height: 1.55; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 24px 0; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 16px; }}
    .label {{ color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }}
    .value {{ font-size: 1.75rem; margin-top: 6px; font-weight: 700; }}
    form {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: end; margin: 22px 0; }}
    label {{ color: var(--muted); display: grid; gap: 6px; font-size: .86rem; }}
    select, input, button {{
      min-height: 40px;
      border-radius: 12px;
      border: 1px solid var(--line);
      padding: 8px 10px;
      background: #fff;
      color: var(--ink);
    }}
    button {{ background: var(--ink); color: #fff; cursor: pointer; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 18px; overflow: hidden; }}
    th {{ background: var(--ink); color: #fff; text-align: left; font-size: .76rem; letter-spacing: .04em; }}
    th, td {{ padding: 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    .rank {{ color: var(--warm); font-size: 1.28rem; font-weight: 800; }}
    .why {{ max-width: 380px; line-height: 1.42; }}
    span {{ color: var(--muted); }}
    .note {{ color: var(--muted); font-size: .92rem; line-height: 1.45; margin-top: 18px; }}
    @media (max-width: 850px) {{
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      table {{ font-size: .88rem; }}
      th:nth-child(6), td:nth-child(6), th:nth-child(7), td:nth-child(7) {{ display: none; }}
    }}
    @media (max-width: 560px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .hero {{ padding: 22px; border-radius: 20px; }}
      th:nth-child(5), td:nth-child(5) {{ display: none; }}
    }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <div class="label">Operational decision support prototype</div>
    <h1>NYC heating complaint risk dashboard</h1>
    <p class="subtitle">
      This dashboard turns the calibrated logistic ranking into an inspector-facing view:
      which buildings should be checked first, why they are risky, and how the priority list
      changes by borough. It supports decisions; it does not automate enforcement.
    </p>
    <div class="grid">
      <div class="card"><div class="label">Priority date</div><div class="value">{escape(latest_date)}</div></div>
      <div class="card"><div class="label">Rows shown</div><div class="value">{len(rows)}</div></div>
      <div class="card"><div class="label">Avg risk</div><div class="value">{avg_probability * 100:.1f}%</div></div>
      <div class="card"><div class="label">Test AUC / P@50</div><div class="value">{test_metrics.get('roc_auc', 'n/a')} / {ranking_50.get('mean_precision_at_k', 'n/a')}</div></div>
    </div>
    <form method="get" action="/dashboard">
      <label>Borough
        <select name="borough">
          {''.join(borough_options)}
        </select>
      </label>
      <label>Top N
        <input name="top_n" type="number" min="1" max="50" value="{top_n}">
      </label>
      <button type="submit">Update view</button>
    </form>
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Building</th>
          <th>Borough</th>
          <th>Risk</th>
          <th>Equity score</th>
          <th>Open violations</th>
          <th>Prior complaints</th>
          <th>Why risky</th>
        </tr>
      </thead>
      <tbody>
        {''.join(row_html)}
      </tbody>
    </table>
    <p class="note">
      Evidence line: API artifacts are loaded from {escape(artifact_source().get('type', 'unknown'))};
      max risk in current view is {max_probability * 100:.1f}%. Show this page with
      <code>/health</code>, <code>/metadata</code>, <code>/priorities/latest</code>, <code>/records/{{building_id}}</code>,
      and <code>/score</code> outputs for a complete class demo.
    </p>
  </section>
</main>
</body>
</html>"""


def score_rows(rows: list[dict[str, Any]]) -> list[ScoreResponseRow]:
    model, calibrator, metadata = model_components()
    frame = prepare_feature_frame(pd.DataFrame(rows), compute_target=False)
    raw_probabilities = model.predict_proba(frame[MODEL_INPUT_COLUMNS])[:, 1]
    probabilities = apply_calibration(calibrator, raw_probabilities)
    threshold = float(metadata["threshold"])
    explanations = explain_model_rows(model=model, metadata=metadata, rows=rows, top_n=5)

    responses: list[ScoreResponseRow] = []
    for index, probability in enumerate(probabilities):
        explanation = explanations[index]
        responses.append(
            ScoreResponseRow(
                probability=round(float(probability), 6),
                threshold=threshold,
                prediction=int(probability >= threshold),
                why_risky=str(explanation["why_risky"]),
                top_positive_contributors=explanation["top_positive_contributors"],
                top_negative_contributors=explanation["top_negative_contributors"],
            )
        )
    return responses


@app.get("/health")
def health() -> dict[str, Any]:
    model_error = None
    metadata: dict[str, Any] = {}
    try:
        _, _, metadata = model_components()
        model_accessible = True
    except Exception as exc:
        model_accessible = False
        model_error = str(exc)

    priority_csv_loaded = True
    priority_row_count = None
    priority_error = None
    try:
        priority_rows = load_priority_frame()
        priority_row_count = int(len(priority_rows))
    except Exception as exc:
        priority_csv_loaded = False
        priority_error = str(exc)

    lookup_db_accessible = record_lookup_db_is_available()
    scored_accessible = scored_csv_is_available()
    scored_readable = scored_csv_is_readable()
    s3_ok = _check_s3_health()
    return {
        "status": "ok" if model_accessible and priority_csv_loaded else "degraded",
        "model_type": metadata.get("model_type"),
        "threshold": metadata.get("threshold"),
        "model_accessible": model_accessible,
        "model_error": model_error,
        "priority_accessible": priority_csv_loaded,
        "lookup_db_accessible": lookup_db_accessible,
        "scored_accessible": scored_accessible,
        "s3_connectivity": s3_ok,
        "artifact_source": artifact_source(),
        # Backward-compatible fields used by the class demo proof script.
        "record_lookup_db_loaded": lookup_db_accessible,
        "scored_csv_present": scored_accessible,
        "scored_csv_readable": scored_readable,
        "scored_row_count": scored_row_count_from_metadata(metadata) if model_accessible else None,
        "priority_csv_loaded": priority_csv_loaded,
        "priority_row_count": priority_row_count,
        "priority_error": priority_error,
    }


def _check_s3_health() -> bool:
    if not S3_BUCKET:
        return False
    try:
        return bool(head_s3_object(S3_BUCKET, S3_MODEL_KEY, region_name=AWS_REGION))
    except Exception:
        return False


@app.get("/metadata")
def metadata() -> dict[str, Any]:
    _, _, info = model_components()
    priority_rows = load_priority_frame()
    latest_date = (
        str(priority_rows["calendar_date"].iloc[0])
        if not priority_rows.empty and "calendar_date" in priority_rows.columns
        else latest_priority_date_from_metadata(info)
    )
    return {
        **info,
        "artifact_source": artifact_source(),
        "latest_priority_date": latest_date,
        "scored_row_count": scored_row_count_from_metadata(info),
        "priority_row_count": int(len(priority_rows)),
    }


@app.get("/priorities/latest")
def latest_priorities(top_n: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    frame = load_priority_frame()
    if frame.empty:
        raise HTTPException(status_code=404, detail="No priority rows available.")
    latest_date = str(frame["calendar_date"].iloc[0]) if "calendar_date" in frame.columns else "n/a"
    latest_rows = frame.sort_values(
        "inspection_priority_rank" if "inspection_priority_rank" in frame.columns else "model_probability",
        ascending=True if "inspection_priority_rank" in frame.columns else False,
    ).head(top_n)
    return {
        "priority_date": latest_date,
        "top_n": top_n,
        "rows": [to_jsonable_record(row) for row in latest_rows.to_dict(orient="records")],
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    top_n: int = Query(default=20, ge=1, le=50),
    borough: Optional[str] = Query(default=None),
) -> HTMLResponse:
    _, _, info = model_components()
    frame = load_priority_frame()
    return HTMLResponse(render_dashboard_html(frame=frame, top_n=top_n, borough_filter=borough, metadata=info))


@app.get("/records/{building_id}")
def building_record(
    building_id: str,
    calendar_date: str = Query(..., description="Calendar date in YYYY-MM-DD format."),
) -> dict[str, Any]:
    priority_rows = load_priority_frame()
    matches = priority_rows[
        (priority_rows["building_id"] == str(building_id)) & (priority_rows["calendar_date"] == str(calendar_date))
    ]
    if not matches.empty:
        row = to_jsonable_record(matches.sort_values("model_probability", ascending=False).iloc[0].to_dict())
        return {"row": row}

    row = find_record_in_lookup_db(building_id=building_id, calendar_date=calendar_date)
    if row is None:
        row = find_record_in_scored_csv(building_id=building_id, calendar_date=calendar_date)
    if row is None:
        raise HTTPException(status_code=404, detail="No scored record found for this building/date.")
    return {"row": to_jsonable_record(row)}


@app.post("/score")
def score(request: ScoreRequest) -> dict[str, Any]:
    return {"rows": [row.dict() for row in score_rows(request.rows)]}
