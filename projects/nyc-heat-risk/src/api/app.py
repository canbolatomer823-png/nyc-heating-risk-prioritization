from __future__ import annotations

import os
import json
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
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
SHAREABLE_SHOWCASE_PATHS = [
    WORKSPACE_ROOT / "docs/index.html",
    PROJECT_ROOT / "outputs/shareable-site/index.html",
]

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


def format_metric(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    try:
        if pd.isna(value):
            return "n/a"
    except (TypeError, ValueError):
        pass
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_project_showcase_html(frame: pd.DataFrame, metadata: dict[str, Any]) -> str:
    if frame.empty:
        raise HTTPException(status_code=404, detail="No priority rows available.")

    ranked = frame.sort_values(
        "inspection_priority_rank" if "inspection_priority_rank" in frame.columns else "model_probability",
        ascending=True if "inspection_priority_rank" in frame.columns else False,
    ).copy()
    top_rows = ranked.head(50)
    latest_date = str(frame["calendar_date"].iloc[0]) if "calendar_date" in frame.columns else latest_priority_date_from_metadata(metadata)
    test_metrics = metadata.get("metrics", {}).get("test", {})
    ranking_metrics = metadata.get("ranking_metrics", {})
    ranking_50 = ranking_metrics.get("50", {})
    scored_rows = scored_row_count_from_metadata(metadata)
    top_probability = float(top_rows["model_probability"].max()) if "model_probability" in top_rows and not top_rows.empty else 0.0
    borough_count = int(top_rows["borough"].nunique()) if "borough" in top_rows else 0
    priority_records = [to_jsonable_record(row) for row in top_rows.to_dict(orient="records")]
    priority_json = json.dumps(priority_records, ensure_ascii=False).replace("</", "<\\/")
    ranking_json = json.dumps(ranking_metrics, ensure_ascii=False).replace("</", "<\\/")
    artifact_type = escape(artifact_source().get("type", "unknown"))

    return f"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NYC Heating Risk | Proje Hikayesi</title>
  <style>
    :root {{
      --ink:#17231f;
      --muted:#596b62;
      --forest:#143f36;
      --forest-2:#0f6b55;
      --brick:#d95f43;
      --gold:#c6922e;
      --paper:#f6ecdc;
      --cream:#fffaf0;
      --mist:#dfece8;
      --line:rgba(23,35,31,.16);
      --shadow:0 24px 70px rgba(31,44,38,.14);
    }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{
      margin:0;
      color:var(--ink);
      background:
        radial-gradient(circle at 8% 4%, rgba(217,95,67,.28), transparent 28%),
        radial-gradient(circle at 88% 8%, rgba(20,63,54,.24), transparent 24%),
        linear-gradient(135deg, #f8f0e1 0%, #e6f0eb 52%, #fff7e9 100%);
      font-family:"Avenir Next", "Gill Sans", "Trebuchet MS", sans-serif;
    }}
    body::before {{
      content:"";
      position:fixed;
      inset:0;
      pointer-events:none;
      opacity:.24;
      background-image:
        linear-gradient(rgba(20,63,54,.14) 1px, transparent 1px),
        linear-gradient(90deg, rgba(20,63,54,.14) 1px, transparent 1px);
      background-size:48px 48px;
      mask-image:linear-gradient(to bottom, black, transparent 78%);
    }}
    a {{ color:inherit; text-decoration:none; }}
    button, input, select {{ font:inherit; }}
    .shell {{ width:min(1180px, calc(100% - 34px)); margin:0 auto; padding:28px 0 52px; position:relative; }}
    .hero {{
      display:grid;
      grid-template-columns:1.08fr .92fr;
      gap:22px;
      align-items:stretch;
      min-height:560px;
      animation:rise .55s ease both;
    }}
    .hero-main, .glass {{
      border:1px solid var(--line);
      border-radius:34px;
      background:rgba(255,250,240,.82);
      box-shadow:var(--shadow);
      backdrop-filter:blur(16px);
    }}
    .hero-main {{ padding:38px; display:flex; flex-direction:column; justify-content:space-between; overflow:hidden; position:relative; }}
    .hero-main::after {{
      content:"";
      position:absolute;
      width:280px;
      height:280px;
      right:-80px;
      bottom:-90px;
      border-radius:50%;
      background:radial-gradient(circle, rgba(217,95,67,.28), transparent 68%);
    }}
    .kicker {{
      display:inline-flex;
      width:max-content;
      gap:9px;
      align-items:center;
      border:1px solid rgba(20,63,54,.18);
      border-radius:999px;
      padding:9px 13px;
      background:#fff8eb;
      color:var(--forest);
      font-size:.82rem;
      font-weight:800;
      letter-spacing:.06em;
      text-transform:uppercase;
    }}
    h1, h2, .serif {{ font-family:Georgia, "Times New Roman", serif; }}
    h1 {{
      margin:26px 0 18px;
      max-width:760px;
      font-size:clamp(3.1rem, 7.8vw, 6.8rem);
      line-height:.88;
      letter-spacing:-.075em;
    }}
    .lead {{ max-width:680px; color:var(--muted); font-size:1.16rem; line-height:1.58; }}
    .cta-row {{ display:flex; flex-wrap:wrap; gap:12px; margin-top:28px; }}
    .btn {{
      border:0;
      border-radius:999px;
      padding:13px 17px;
      cursor:pointer;
      font-weight:800;
      background:var(--forest);
      color:white;
      box-shadow:0 14px 24px rgba(20,63,54,.18);
    }}
    .btn.alt {{ background:#fff8eb; color:var(--forest); border:1px solid var(--line); box-shadow:none; }}
    .glass {{ padding:24px; display:grid; gap:16px; }}
    .metric-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:13px; }}
    .metric {{
      min-height:132px;
      border-radius:24px;
      padding:18px;
      background:linear-gradient(160deg,#fffdf7,#edf6f2);
      border:1px solid rgba(20,63,54,.12);
    }}
    .metric .label {{ color:var(--muted); font-size:.79rem; text-transform:uppercase; letter-spacing:.08em; font-weight:800; }}
    .metric .value {{ margin-top:13px; font-size:2.05rem; font-weight:900; letter-spacing:-.04em; }}
    .metric.wide {{ grid-column:1 / -1; background:linear-gradient(145deg,var(--forest),#1c6b58); color:white; }}
    .metric.wide .label {{ color:#cfe3dc; }}
    .nav {{
      display:flex;
      flex-wrap:wrap;
      gap:10px;
      margin:22px 0;
      padding:10px;
      border:1px solid var(--line);
      border-radius:999px;
      background:rgba(255,250,240,.72);
      backdrop-filter:blur(12px);
      position:sticky;
      top:12px;
      z-index:5;
    }}
    .nav button {{
      border:0;
      border-radius:999px;
      padding:11px 14px;
      background:transparent;
      color:var(--muted);
      cursor:pointer;
      font-weight:800;
    }}
    .nav button.active {{ background:var(--forest); color:white; }}
    .section {{
      display:none;
      border:1px solid var(--line);
      border-radius:32px;
      background:rgba(255,250,240,.82);
      box-shadow:var(--shadow);
      padding:28px;
      margin-top:18px;
      animation:rise .35s ease both;
    }}
    .section.active {{ display:block; }}
    .section h2 {{ margin:0 0 8px; font-size:clamp(2rem,4vw,3.5rem); letter-spacing:-.05em; }}
    .section-intro {{ color:var(--muted); max-width:760px; line-height:1.55; font-size:1.04rem; }}
    .pipeline {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-top:22px; }}
    .pipe-card {{
      border:1px solid var(--line);
      border-radius:22px;
      padding:18px;
      background:#fffdf7;
      min-height:170px;
      position:relative;
      overflow:hidden;
    }}
    .pipe-card::before {{ content:attr(data-step); color:rgba(217,95,67,.18); font-size:4rem; font-weight:900; position:absolute; right:12px; bottom:-14px; }}
    .pipe-card b {{ display:block; color:var(--forest); font-size:1.02rem; margin-bottom:9px; }}
    .pipe-card p {{ margin:0; color:var(--muted); line-height:1.42; font-size:.94rem; }}
    .methods {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-top:22px; }}
    .method {{
      border-radius:24px;
      padding:18px;
      background:#fffdf7;
      border:1px solid var(--line);
      min-height:190px;
    }}
    .method strong {{ display:block; color:var(--brick); font-size:1.12rem; margin-bottom:8px; }}
    .formula {{ margin-top:12px; padding:11px; border-radius:14px; background:#18352f; color:#fff8e8; font-family:"SF Mono", Menlo, Consolas, monospace; font-size:.84rem; line-height:1.45; }}
    .sim-layout {{ display:grid; grid-template-columns:.95fr 1.05fr; gap:20px; margin-top:22px; }}
    .control-panel, .detail-panel {{
      border:1px solid var(--line);
      border-radius:26px;
      background:#fffdf7;
      padding:20px;
    }}
    .slider-row {{ display:grid; gap:10px; margin:16px 0; }}
    input[type=range] {{ width:100%; accent-color:var(--brick); }}
    select {{
      width:100%;
      border:1px solid var(--line);
      border-radius:14px;
      min-height:44px;
      background:white;
      padding:8px 11px;
      color:var(--ink);
    }}
    .result-grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin-top:14px; }}
    .result {{ border-radius:18px; background:var(--mist); padding:14px; }}
    .result span {{ display:block; color:var(--muted); font-size:.78rem; text-transform:uppercase; font-weight:800; }}
    .result b {{ display:block; margin-top:6px; font-size:1.55rem; }}
    .priority-grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin-top:16px; max-height:590px; overflow:auto; padding-right:4px; }}
    .risk-card {{
      border:1px solid var(--line);
      border-radius:20px;
      background:#fffdf7;
      padding:15px;
      cursor:pointer;
      transition:transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }}
    .risk-card:hover {{ transform:translateY(-3px); border-color:rgba(217,95,67,.5); box-shadow:0 14px 28px rgba(31,44,38,.12); }}
    .risk-card.active {{ border-color:var(--brick); box-shadow:0 0 0 3px rgba(217,95,67,.12); }}
    .risk-top {{ display:flex; justify-content:space-between; gap:10px; align-items:flex-start; }}
    .rank {{ color:var(--brick); font-weight:950; font-size:1.35rem; }}
    .risk {{ font-weight:900; color:var(--forest); }}
    .small {{ color:var(--muted); font-size:.88rem; line-height:1.4; }}
    .detail-panel h3 {{ margin:0 0 8px; font-size:1.5rem; }}
    .detail-panel .why {{ margin:14px 0; padding:14px; border-radius:18px; background:#f1e2cd; color:#3a3026; line-height:1.45; }}
    .endpoint-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-top:18px; }}
    .endpoint {{
      display:block;
      border-radius:20px;
      padding:16px;
      min-height:126px;
      background:#fffdf7;
      border:1px solid var(--line);
    }}
    .endpoint b {{ color:var(--forest); }}
    .endpoint span {{ display:block; margin-top:8px; color:var(--muted); font-size:.9rem; line-height:1.35; }}
    pre {{
      white-space:pre-wrap;
      word-break:break-word;
      border-radius:18px;
      background:#13241f;
      color:#e9fff5;
      padding:16px;
      max-height:260px;
      overflow:auto;
    }}
    @keyframes rise {{ from {{ opacity:0; transform:translateY(16px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @media (max-width:960px) {{
      .hero, .sim-layout {{ grid-template-columns:1fr; min-height:auto; }}
      .pipeline, .methods, .endpoint-grid {{ grid-template-columns:repeat(2,1fr); }}
    }}
    @media (max-width:640px) {{
      .shell {{ width:min(100% - 22px, 1180px); padding-top:14px; }}
      .hero-main, .glass, .section {{ border-radius:24px; padding:20px; }}
      .metric-grid, .pipeline, .methods, .priority-grid, .endpoint-grid, .result-grid {{ grid-template-columns:1fr; }}
      .nav {{ border-radius:24px; position:static; }}
      .nav button {{ width:100%; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="hero-main">
        <div>
          <div class="kicker">IST-312 final projesi · çalışan karar destek prototipi</div>
          <h1>Isınma şikayetini beklemeden riskli binaları sırala.</h1>
          <p class="lead">Bu sayfa projeyi sınıfta daha anlaşılır göstermek için hazırlandı: problem, resmi veri kaynakları, istatistik yöntemleri, Top-50 öncelik listesi, API kanıtı ve AWS yaklaşımı tek akışta.</p>
        </div>
        <div class="cta-row">
          <a class="btn" href="/dashboard?top_n=10">Operasyonel dashboard'u aç</a>
          <a class="btn alt" href="/priorities/latest?top_n=5">Top-5 JSON kanıtı</a>
          <a class="btn alt" href="/health">API sağlığı</a>
        </div>
      </div>
      <aside class="glass">
        <div class="metric wide">
          <div class="label">Tek karar sorusu</div>
          <div class="value serif">Yarın önce hangi binalara gidilmeli?</div>
        </div>
        <div class="metric">
          <div class="label">Model satırı</div>
          <div class="value">{scored_rows:,}</div>
        </div>
        <div class="metric">
          <div class="label">Son skor tarihi</div>
          <div class="value">{escape(latest_date)}</div>
        </div>
        <div class="metric">
          <div class="label">Test AUC</div>
          <div class="value">{escape(format_metric(test_metrics.get("roc_auc")))}</div>
        </div>
        <div class="metric">
          <div class="label">Lift@50</div>
          <div class="value">{escape(format_metric(ranking_50.get("mean_lift_at_k"), 1))}x</div>
        </div>
      </aside>
    </section>

    <nav class="nav" aria-label="Proje bölümleri">
      <button class="active" data-section="story">1. Hikaye</button>
      <button data-section="data">2. Veri akışı</button>
      <button data-section="methods">3. İstatistik</button>
      <button data-section="simulation">4. İnteraktif çıktı</button>
      <button data-section="proof">5. Kanıt ve dağıtım</button>
    </nav>

    <section id="story" class="section active">
      <h2>Problem insan problemi, çıktı karar listesi.</h2>
      <p class="section-intro">Soğuk dönemde ısınma veya sıcak su sorunu yaşayan binalar için denetim kapasitesi sınırlı. Proje arızayı fiziksel olarak tamir etmez; resmi verilerle hangi binaların önce incelenmesi gerektiğini sıralar.</p>
      <div class="pipeline">
        <div class="pipe-card" data-step="01"><b>İnsan sorunu</b><p>Isınma ve sıcak su yokluğu temel yaşam hizmetini etkiler.</p></div>
        <div class="pipe-card" data-step="02"><b>Karar sorusu</b><p>Denetçi yarın önce hangi binalara gitmeli?</p></div>
        <div class="pipe-card" data-step="03"><b>Risk skoru</b><p>Her bina-gün için şikayet olasılığı üretilir.</p></div>
        <div class="pipe-card" data-step="04"><b>Top-50 liste</b><p>Olasılıklar büyükten küçüğe sıralanır.</p></div>
        <div class="pipe-card" data-step="05"><b>Karar desteği</b><p>Sistem öneri verir; otomatik ceza kararı vermez.</p></div>
      </div>
    </section>

    <section id="data" class="section">
      <h2>Resmi veri kaynakları tek bina-gün panelinde birleşiyor.</h2>
      <p class="section-intro">Sahte veri yok. Modelin karar birimi <b>bir bina + bir gün</b>. Geleceği görmemesi için bugün bilinen bilgilerle ertesi gün tahmin edilir: <b>X(i,t) → Y(i,t+1)</b>.</p>
      <div class="pipeline">
        <div class="pipe-card" data-step="311"><b>NYC 311</b><p>Vatandaşların belediyeye ilettiği ısınma ve sıcak su şikayetleri.</p></div>
        <div class="pipe-card" data-step="HPD"><b>HPD</b><p>Bina, ihlal, konut bakım ve ısı sensörü programı kayıtları.</p></div>
        <div class="pipe-card" data-step="WX"><b>NOAA</b><p>Günlük sıcaklık, yağış, rüzgar ve soğukluk göstergeleri.</p></div>
        <div class="pipe-card" data-step="CRE"><b>Census CRE</b><p>Sosyal ve çevresel kırılganlık katmanı.</p></div>
        <div class="pipe-card" data-step="t+1"><b>Sızıntı denetimi</b><p>t günündeki bilgi kullanılır; t+1 günündeki şikayet hedef olur.</p></div>
      </div>
    </section>

    <section id="methods" class="section">
      <h2>Yöntemler aynı sorunun farklı yüzlerini kontrol ediyor.</h2>
      <p class="section-intro">Ana operasyonel model lojistik regresyondur. Diğer yöntemler veri hikayesini, sayı yapısını ve aynı binanın tekrar gözlenmesini istatistiksel olarak kontrol eder.</p>
      <div class="methods">
        <div class="method"><strong>ANOVA</strong><p>Ayların ortalama şikayet yükü aynı mı diye test ettim.</p><div class="formula">H0: μOct = ... = μMay<br>F = MS_between / MS_within<br>F=33.62, p&lt;0.0001</div></div>
        <div class="method"><strong>Lojistik regresyon</strong><p>Ertesi gün şikayet var/yok olasılığı için ana karar modeli.</p><div class="formula">Y(i,t+1) ~ Bernoulli(p)<br>logit(p)=β0+βX<br>p → Top-50</div></div>
        <div class="method"><strong>Negatif Binom</strong><p>Şikayet sayısı gibi aşırı değişken sayım verisini kontrol eder.</p><div class="formula">Y_count ~ NB(μ, θ)<br>log(μ)=β0+βX<br>Var(Y)&gt;E(Y)</div></div>
        <div class="method"><strong>GEE</strong><p>Aynı binanın birçok gün tekrar gözlenmesini cluster mantığıyla ele alır.</p><div class="formula">cluster = building_id<br>tekrar ölçüm bağımlılığı<br>sağlam standart hata</div></div>
        <div class="method"><strong>GLMM</strong><p>Her binanın kendine özgü başlangıç riskini random intercept ile kontrol eder.</p><div class="formula">random intercept: bina<br>ana kanıt değil<br>tanısal kontrol</div></div>
        <div class="method"><strong>Kalibrasyon ve sıralama</strong><p>Nadir olayda amaç sadece sınıflandırmak değil, en riskli binaları üstte toplamaktır.</p><div class="formula">AUC={escape(format_metric(test_metrics.get("roc_auc")))}<br>P@50={escape(format_metric(ranking_50.get("mean_precision_at_k")))}<br>Lift@50={escape(format_metric(ranking_50.get("mean_lift_at_k"), 1))}x</div></div>
      </div>
    </section>

    <section id="simulation" class="section">
      <h2>İnteraktif çıktı: kapasiteyi değiştir, öncelik listesini incele.</h2>
      <p class="section-intro">Bu bölüm sınıfta “model sonucu gerçek karara nasıl dönüşüyor?” sorusuna cevap verir. Kapasiteyi ve ilçeyi değiştir; risk kartına tıklayınca neden riskli görüldüğünü gösterir.</p>
      <div class="sim-layout">
        <div class="control-panel">
          <label class="slider-row"><b>Günlük denetim kapasitesi: <span id="capacityLabel">50</span> bina</b>
            <input id="capacity" type="range" min="10" max="100" value="50" step="5">
          </label>
          <label class="slider-row"><b>İlçe filtresi</b>
            <select id="boroughFilter"></select>
          </label>
          <div class="result-grid">
            <div class="result"><span>Beklenen isabet</span><b id="expectedHits">-</b></div>
            <div class="result"><span>Rastgele beklenti</span><b id="randomHits">-</b></div>
            <div class="result"><span>Precision@K</span><b id="precisionK">-</b></div>
            <div class="result"><span>Lift@K</span><b id="liftK">-</b></div>
          </div>
          <p class="small">Not: Simülasyon eğitimdeki ranking metriklerinden hesaplanan karar desteği özetidir; otomatik denetim kararı değildir.</p>
        </div>
        <div class="detail-panel">
          <h3 id="detailTitle">Risk kartı seç</h3>
          <p id="detailMeta" class="small">Aşağıdaki kartlardan bir binaya tıkla.</p>
          <div id="detailWhy" class="why">Modelin kısa açıklaması burada görünecek.</div>
          <p id="detailStats" class="small"></p>
        </div>
      </div>
      <div id="priorityGrid" class="priority-grid" aria-live="polite"></div>
    </section>

    <section id="proof" class="section">
      <h2>Çalışma kanıtı: API, dashboard, Docker ve AWS zinciri.</h2>
      <p class="section-intro">Bu sayfa etkileyici giriş; gerçek çalışma kanıtı endpoint'ler ve raporlardır. AWS kalıcı açık tutulmaz, maliyet oluşmaması için kısa deploy kanıtı ve kapatma kanıtı gösterilir.</p>
      <div class="endpoint-grid">
        <a class="endpoint" href="/health"><b>/health</b><span>Model, öncelik CSV, lookup DB ve artifact kaynağı sağlıklı mı?</span></a>
        <a class="endpoint" href="/metadata"><b>/metadata</b><span>Model türü, eşik, metrikler ve son skor tarihi.</span></a>
        <a class="endpoint" href="/priorities/latest?top_n=5"><b>/priorities/latest</b><span>Top-N denetim öncelik listesinin JSON çıktısı.</span></a>
        <a class="endpoint" href="/dashboard?top_n=10"><b>/dashboard</b><span>Saha ekibinin kullanacağı operasyonel tablo.</span></a>
      </div>
      <div class="cta-row">
        <button class="btn" id="apiCheck">Canlı API kontrolü çalıştır</button>
        <span class="small">Artifact kaynağı: {artifact_type}. En yüksek mevcut risk: {top_probability * 100:.1f}%. İlk 50 listede {borough_count} ilçe var.</span>
      </div>
      <pre id="apiOutput">Düğmeye basınca /health ve /metadata kısa özeti burada görünecek.</pre>
    </section>
  </main>
  <script>
    const priorityRows = {priority_json};
    const rankingMetrics = {ranking_json};

    const sections = document.querySelectorAll('.section');
    const navButtons = document.querySelectorAll('.nav button');
    navButtons.forEach((button) => {{
      button.addEventListener('click', () => {{
        navButtons.forEach((item) => item.classList.remove('active'));
        sections.forEach((section) => section.classList.remove('active'));
        button.classList.add('active');
        document.getElementById(button.dataset.section).classList.add('active');
      }});
    }});

    const capacity = document.getElementById('capacity');
    const capacityLabel = document.getElementById('capacityLabel');
    const boroughFilter = document.getElementById('boroughFilter');
    const grid = document.getElementById('priorityGrid');
    const detailTitle = document.getElementById('detailTitle');
    const detailMeta = document.getElementById('detailMeta');
    const detailWhy = document.getElementById('detailWhy');
    const detailStats = document.getElementById('detailStats');

    function asNumber(value, fallback = 0) {{
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : fallback;
    }}

    function pct(value, digits = 1) {{
      return `${{(asNumber(value) * 100).toFixed(digits)}}%`;
    }}

    function nearestMetric(k) {{
      const keys = Object.keys(rankingMetrics).map(Number).sort((a, b) => a - b);
      let best = keys[0] || 50;
      for (const key of keys) {{
        if (Math.abs(key - k) < Math.abs(best - k)) best = key;
      }}
      return {{ key: best, metric: rankingMetrics[String(best)] || {{}} }};
    }}

    function updateCapacity() {{
      const k = Number(capacity.value);
      capacityLabel.textContent = k;
      const {{ key, metric }} = nearestMetric(k);
      const precision = asNumber(metric.mean_precision_at_k);
      const lift = asNumber(metric.mean_lift_at_k);
      const expected = precision * k;
      const random = lift > 0 ? expected / lift : 0;
      document.getElementById('expectedHits').textContent = expected.toFixed(1);
      document.getElementById('randomHits').textContent = random.toFixed(2);
      document.getElementById('precisionK').textContent = `${{pct(precision)}} (K≈${{key}})`;
      document.getElementById('liftK').textContent = lift ? `${{lift.toFixed(1)}}x` : 'n/a';
      renderCards();
    }}

    function setupBoroughs() {{
      const boroughs = [...new Set(priorityRows.map((row) => row.borough).filter(Boolean))].sort();
      boroughFilter.innerHTML = '<option value="ALL">Tüm ilçeler</option>' + boroughs.map((borough) => `<option value="${{borough}}">${{borough}}</option>`).join('');
    }}

    function selectedRows() {{
      const chosen = boroughFilter.value;
      const limit = Number(capacity.value);
      return priorityRows
        .filter((row) => chosen === 'ALL' || row.borough === chosen)
        .slice(0, Math.min(limit, 50));
    }}

    function renderCards() {{
      const rows = selectedRows();
      if (!rows.length) {{
        grid.innerHTML = '<div class="risk-card">Bu filtre için kayıt yok.</div>';
        return;
      }}
      grid.innerHTML = rows.map((row, index) => {{
        const risk = pct(row.model_probability);
        const rank = row.inspection_priority_rank || index + 1;
        const address = row.incident_address || 'Adres yok';
        const why = row.why_risky || 'Açıklama yok';
        return `<article class="risk-card" data-index="${{priorityRows.indexOf(row)}}">
          <div class="risk-top"><span class="rank">#${{rank}}</span><span class="risk">${{risk}}</span></div>
          <b>${{row.building_id || 'Bina yok'}}</b>
          <p class="small">${{row.borough || '-'}} · ${{address}}</p>
          <p class="small">${{why}}</p>
        </article>`;
      }}).join('');
      document.querySelectorAll('.risk-card[data-index]').forEach((card) => {{
        card.addEventListener('click', () => selectRow(Number(card.dataset.index), card));
      }});
      const first = document.querySelector('.risk-card[data-index]');
      if (first) first.click();
    }}

    function selectRow(index, card) {{
      const row = priorityRows[index];
      document.querySelectorAll('.risk-card').forEach((item) => item.classList.remove('active'));
      if (card) card.classList.add('active');
      detailTitle.textContent = `Bina ${{row.building_id}} · risk ${{pct(row.model_probability)}}`;
      detailMeta.textContent = `${{row.borough || '-'}} · ${{row.incident_address || 'Adres yok'}} · Sıra #${{row.inspection_priority_rank || '-'}}`;
      detailWhy.textContent = row.why_risky || 'Açıklama yok.';
      detailStats.textContent = `Geçmiş şikayet: ${{row.cumulative_complaints_prior ?? '-'}} · Açık ihlal: ${{row.open_linked_violation_count ?? '-'}} · Equity score: ${{asNumber(row.equity_weighted_priority_score).toFixed(3)}}`;
    }}

    document.getElementById('apiCheck').addEventListener('click', async () => {{
      const output = document.getElementById('apiOutput');
      output.textContent = 'Kontrol çalışıyor...';
      try {{
        const [health, metadata] = await Promise.all([
          fetch('/health').then((response) => response.json()),
          fetch('/metadata').then((response) => response.json())
        ]);
        output.textContent = JSON.stringify({{
          health_status: health.status,
          model_type: health.model_type,
          artifact_source: health.artifact_source?.type,
          scored_rows: health.scored_row_count,
          latest_priority_date: metadata.latest_priority_date,
          priority_rows: metadata.priority_row_count,
          threshold: metadata.threshold
        }}, null, 2);
      }} catch (error) {{
        output.textContent = `Kontrol başarısız: ${{error}}`;
      }}
    }});

    capacity.addEventListener('input', updateCapacity);
    boroughFilter.addEventListener('change', renderCards);
    setupBoroughs();
    updateCapacity();
  </script>
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


@app.get("/showcase", response_class=HTMLResponse)
def showcase() -> HTMLResponse:
    for path in SHAREABLE_SHOWCASE_PATHS:
        if path.exists():
            return HTMLResponse(path.read_text(encoding="utf-8"))
    _, _, info = model_components()
    frame = load_priority_frame()
    return HTMLResponse(render_project_showcase_html(frame=frame, metadata=info))


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return showcase()


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
