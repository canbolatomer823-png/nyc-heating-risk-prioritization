from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import (
    FINAL_DENSE_PANEL_PATH,
    FINAL_DRIFT_REPORT_PATH,
    FINAL_ERROR_ANALYSIS_REPORT_PATH,
    FINAL_FAIRNESS_REPORT_PATH,
    FINAL_LOGISTIC_METRICS_PATH,
    FINAL_MODEL_METADATA_PATH,
    FINAL_POLICY_SIMULATION_REPORT_PATH,
    FINAL_PRESENTATION_DECK_PATH,
    FINAL_PRIORITY_CSV_PATH,
    FINAL_PRIORITY_SUMMARY_PATH,
    FINAL_PROJECT_AUDIT_PATH,
    FINAL_RECORD_LOOKUP_DB_PATH,
    FINAL_SEASONAL_ANOVA_REPORT_PATH,
    FINAL_UNCERTAINTY_REPORT_PATH,
    OOT_VALIDATION_REPORT_PATH,
    PROJECT_ROOT,
)


REPORTS_DIR = PROJECT_ROOT / "reports"
MODEL_CARD_PATH = REPORTS_DIR / "model_card.md"
DATA_CARD_PATH = REPORTS_DIR / "data_card.md"
EVIDENCE_PACK_DIR = REPORTS_DIR / "evidence_pack"
EVIDENCE_PACK_README = EVIDENCE_PACK_DIR / "README.md"
EVIDENCE_DASHBOARD_PNG = EVIDENCE_PACK_DIR / "dashboard_summary.png"
DEMO_PROOF_MD = REPORTS_DIR / "demo_proof" / "demo_proof.md"
AWS_LIVE_DEPLOY_PROOF_MD = REPORTS_DIR / "aws_live_deploy_proof.md"
AWS_SHUTDOWN_PROOF_MD = REPORTS_DIR / "aws_shutdown_proof.md"
SUPABASE_READINESS_MD = (
    PROJECT_ROOT
    / "data"
    / "windows"
    / "heat_season_2024_10_01_2025_05_31"
    / "reports"
    / "supabase"
    / "supabase_readiness.md"
)
SUPABASE_LIVE_CHECKLIST = PROJECT_ROOT / "deploy" / "SUPABASE_LIVE_CHECKLIST.md"
SUPABASE_DEMO_SQL = PROJECT_ROOT / "sql" / "06_supabase_demo_queries.sql"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def row_count(path: Path) -> int:
    return sum(len(chunk) for chunk in pd.read_csv(path, chunksize=250_000, usecols=[0]))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    width: int,
    fill: str,
    text_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    line_gap: int = 6,
) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=text_font) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    x, y = xy
    bbox = draw.textbbox((0, 0), "Ag", font=text_font)
    line_height = bbox[3] - bbox[1] + line_gap
    for line in lines:
        draw.text((x, y), line, fill=fill, font=text_font)
        y += line_height
    return y


def draw_metric_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    accent: str,
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=22, fill="#ffffff", outline="#d9e2e7", width=2)
    draw.rectangle((x0, y0, x0 + 9, y1), fill=accent)
    draw.text((x0 + 26, y0 + 22), label.upper(), fill="#607080", font=font(21, bold=True))
    draw.text((x0 + 26, y0 + 58), value, fill="#16202a", font=font(38, bold=True))


def borough_short_name(value: str) -> str:
    lookup = {
        "MANHATTAN": "MANH",
        "BROOKLYN": "BKLYN",
        "STATEN ISLAND": "S.I.",
    }
    return lookup.get(value.upper(), value.upper())


def write_dashboard_preview(metadata: dict[str, Any], output: Path) -> None:
    priority = pd.read_csv(FINAL_PRIORITY_CSV_PATH, nrows=50, low_memory=False)
    top10 = priority.sort_values("inspection_priority_rank").head(10)
    test = metadata.get("metrics", {}).get("test", {})
    ranking_50 = metadata.get("ranking_metrics", {}).get("50", {})
    latest_date = str(priority["calendar_date"].iloc[0]) if not priority.empty else "n/a"
    top = top10.iloc[0].to_dict() if not top10.empty else {}
    borough_counts = priority["borough"].fillna("unknown").astype(str).value_counts().head(5)

    width, height = 1600, 1120
    image = Image.new("RGB", (width, height), "#f4f0e7")
    draw = ImageDraw.Draw(image)
    draw.ellipse((-250, -220, 520, 460), fill="#f0c7b5")
    draw.ellipse((1120, -180, 1850, 520), fill="#c4dce5")
    draw.rounded_rectangle((70, 70, 1530, 1050), radius=38, fill="#fffaf0", outline="#d7d0c3", width=2)

    draw.text((110, 105), "NYC Heating Risk - Evidence Dashboard", fill="#16202a", font=font(54, bold=True))
    draw.text(
        (112, 170),
        "Real official-data prototype: top-risk buildings, explanations, ranking metrics, and operational mix.",
        fill="#607080",
        font=font(25),
    )

    draw_metric_card(draw, (110, 230, 435, 350), "Priority date", latest_date, "#d95d39")
    draw_metric_card(draw, (455, 230, 780, 350), "Held-out AUC", fmt(test.get("roc_auc")), "#1f6f8b")
    draw_metric_card(draw, (800, 230, 1125, 350), "Precision@50", fmt(ranking_50.get("mean_precision_at_k")), "#2f855a")
    draw_metric_card(draw, (1145, 230, 1470, 350), "Lift@50", fmt(ranking_50.get("mean_lift_at_k")), "#b7791f")

    draw.text((110, 410), "Top 10 prioritized buildings", fill="#16202a", font=font(32, bold=True))
    bar_x, bar_y = 110, 465
    max_prob = max(float(top10["model_probability"].max()), 0.01) if not top10.empty else 1.0
    for index, row in enumerate(top10.to_dict(orient="records")):
        y = bar_y + index * 39
        prob = float(row.get("model_probability", 0.0))
        bar_width = int(470 * prob / max_prob)
        label = f"#{int(row.get('inspection_priority_rank', index + 1))} {row.get('building_id')} {row.get('borough', '')}"
        draw.text((bar_x, y), label[:30], fill="#16202a", font=font(20, bold=True))
        draw.rounded_rectangle((bar_x + 265, y + 3, bar_x + 735, y + 25), radius=10, fill="#eadfd2")
        draw.rounded_rectangle((bar_x + 265, y + 3, bar_x + 265 + bar_width, y + 25), radius=10, fill="#d95d39")
        draw.text((bar_x + 755, y), percent(prob), fill="#16202a", font=font(20, bold=True))

    draw.text((930, 410), "Borough mix in top 50", fill="#16202a", font=font(32, bold=True))
    chart_x, chart_y = 930, 470
    max_count = max(int(borough_counts.max()), 1) if not borough_counts.empty else 1
    colors = ["#d95d39", "#1f6f8b", "#2f855a", "#b7791f", "#5b5f97"]
    for index, (borough, count) in enumerate(borough_counts.items()):
        x = chart_x + index * 112
        bar_height = int(240 * int(count) / max_count)
        draw.rounded_rectangle((x, chart_y + 250 - bar_height, x + 70, chart_y + 250), radius=12, fill=colors[index % len(colors)])
        draw.text((x + 18, chart_y + 258), str(int(count)), fill="#16202a", font=font(23, bold=True))
        draw.text((x - 2, chart_y + 292), borough_short_name(str(borough)), fill="#607080", font=font(18, bold=True))

    draw.rounded_rectangle((930, 815, 1470, 965), radius=22, fill="#ffffff", outline="#d9e2e7", width=2)
    draw.text((955, 838), "Top building explanation", fill="#607080", font=font(20, bold=True))
    explanation = str(top.get("why_risky", "No explanation available."))
    draw_wrapped(draw, (955, 870), explanation, 480, "#16202a", font(20), line_gap=5)

    draw.text(
        (110, 990),
        "Use with /health, /metadata, /priorities/latest, /dashboard and Supabase SQL demo queries.",
        fill="#607080",
        font=font(22),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def write_model_card(metadata: dict[str, Any], output: Path) -> None:
    test = metadata.get("metrics", {}).get("test", {})
    ranking_50 = metadata.get("ranking_metrics", {}).get("50", {})
    oot_text = OOT_VALIDATION_REPORT_PATH.read_text(encoding="utf-8") if OOT_VALIDATION_REPORT_PATH.exists() else ""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Model Card - NYC Heating Risk",
        "",
        f"- Generated at: `{now}`",
        "- Model role: operational ranking for next-day heating/hot water complaint risk.",
        "- Primary use: prioritize which buildings should be reviewed first when inspection capacity is limited.",
        "- Non-use: do not use as an automatic enforcement or tenant eligibility decision system.",
        "",
        "## Model",
        "",
        f"- Type: `{metadata.get('model_type')}`",
        f"- Calibration: `{metadata.get('calibration_method')}`",
        f"- Decision threshold: `{metadata.get('threshold')}`",
        "- Primary evidence: calibrated logistic ranking, not GLMM.",
        "- Statistical support: GEE, Negative Binomial, ANOVA, R replication, fairness/calibration, uncertainty, drift.",
        "",
        "## Data Split",
        "",
    ]
    for split, dates in metadata.get("date_ranges", {}).items():
        lines.append(f"- `{split}`: `{dates[0]}` -> `{dates[1]}`")
    lines.extend(
        [
            "",
            "## Held-Out Test Metrics",
            "",
            f"- Rows: `{fmt(test.get('rows'))}`",
            f"- Precision: `{fmt(test.get('precision'))}`",
            f"- Recall: `{fmt(test.get('recall'))}`",
            f"- F1: `{fmt(test.get('f1'))}`",
            f"- ROC AUC: `{fmt(test.get('roc_auc'))}`",
            f"- Average precision: `{fmt(test.get('average_precision'))}`",
            f"- Brier score: `{fmt(test.get('brier_score'))}`",
            f"- Mean Precision@50: `{fmt(ranking_50.get('mean_precision_at_k'))}`",
            f"- Mean Lift@50: `{fmt(ranking_50.get('mean_lift_at_k'))}`",
            "",
            "## Out-of-Time Evidence",
            "",
            "- Report: "
            f"[out_of_time_validation.md]({OOT_VALIDATION_REPORT_PATH})",
        ]
    )
    for needle in ["- Precision:", "- Recall:", "- F1:", "- ROC AUC:", "- Mean Precision@50:"]:
        for line in oot_text.splitlines():
            if line.startswith(needle):
                lines.append(line)
                break
    lines.extend(
        [
            "",
            "## Known Limitations",
            "",
            "- This is a decision-support prototype, not an automatic inspection system.",
            "- AWS live deploy should be presented as timestamped proof unless the short-lived endpoint is recreated for demo day.",
            "- GLMM is diagnostic only because optimizer convergence is not strong enough for primary claims.",
            "- The model ranks operational risk; it does not prove causality.",
            "- Equity weighting is transparent and auditable, but it still needs policy review before real use.",
            "",
            "## Linked Evidence",
            "",
            f"- Metrics: [logistic_regression_metrics.md]({FINAL_LOGISTIC_METRICS_PATH})",
            f"- Policy simulation: [inspection_policy_simulation.md]({FINAL_POLICY_SIMULATION_REPORT_PATH})",
            f"- Fairness/calibration: [subgroup_fairness_calibration.md]({FINAL_FAIRNESS_REPORT_PATH})",
            f"- Uncertainty: [uncertainty_report.md]({FINAL_UNCERTAINTY_REPORT_PATH})",
            f"- Drift: [train_test_drift_report.md]({FINAL_DRIFT_REPORT_PATH})",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_data_card(output: Path) -> None:
    priority = pd.read_csv(FINAL_PRIORITY_CSV_PATH, nrows=50, low_memory=False)
    dense_rows = row_count(FINAL_DENSE_PANEL_PATH) if FINAL_DENSE_PANEL_PATH.exists() else 0
    latest_date = str(priority["calendar_date"].iloc[0]) if not priority.empty else "n/a"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Data Card - NYC Heating Risk",
        "",
        f"- Generated at: `{now}`",
        "- Unit of analysis: `building-day`.",
        "- Prediction target: whether a building receives a next-day heat/hot water complaint.",
        "- Final heat-season window: `2024-10-01 -> 2025-05-31`.",
        f"- Dense panel rows: `{dense_rows:,}`",
        f"- Latest priority date: `{latest_date}`",
        "",
        "## Official Data Sources",
        "",
        "- NYC 311 Service Requests from 2010 to Present.",
        "- NYC HPD Housing Maintenance Code Complaints and Problems.",
        "- NYC HPD Buildings Subject to HPD Jurisdiction.",
        "- NYC HPD Multiple Dwelling Registrations.",
        "- NYC HPD Housing Maintenance Code Violations.",
        "- NYC HPD Heat Sensor Program building list.",
        "- NOAA GSOD / GHCN weather data.",
        "- Census Community Resilience Estimates tract-level extract.",
        "",
        "## Feature Groups",
        "",
        "- Complaint history: lag, rolling, cumulative, prior max, days since last complaint.",
        "- Building/admin data: borough, management program, unit proxy, registration status.",
        "- Violations: linked violation counts and open violation counts with as-of leakage controls.",
        "- Weather: temperature, heating-degree load, freezing flags, precipitation, wind, cold shock.",
        "- Equity context: tract-level CRE vulnerability and equity-weather interaction.",
        "",
        "## Quality Controls",
        "",
        "- No duplicate building-date rows in the dense panel.",
        "- No missing weather rows in the dense panel.",
        "- No future-dated violation features.",
        "- No target, lag, rolling, cumulative, prior-max, or days-since mismatch rows.",
        "- CRE coverage is high but not perfect; unmatched tract rows remain disclosed.",
        "",
        "## Data Risks",
        "",
        "- Complaint data reflects reporting behavior, not the full universe of heating failures.",
        "- CRE tract vulnerability is contextual; it should not be interpreted as a building-level causal variable.",
        "- Open-data refreshes can change future model behavior, so drift monitoring is required.",
        "- The project should be presented as heating/hot-water risk, not summer heat-wave risk.",
        "",
        "## Linked Evidence",
        "",
        f"- Panel quality audit: [panel_quality_audit.md]({PROJECT_ROOT / 'data/windows/heat_season_2024_10_01_2025_05_31/reports/panel_quality_audit.md'})",
        f"- Seasonal ANOVA: [seasonal_anova.md]({FINAL_SEASONAL_ANOVA_REPORT_PATH})",
        f"- Priority summary: [inspection_priority_summary.md]({FINAL_PRIORITY_SUMMARY_PATH})",
        f"- Error analysis: [error_analysis.md]({FINAL_ERROR_ANALYSIS_REPORT_PATH})",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_evidence_pack(metadata: dict[str, Any], output: Path) -> None:
    test = metadata.get("metrics", {}).get("test", {})
    ranking_50 = metadata.get("ranking_metrics", {}).get("50", {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Demo Evidence Pack",
        "",
        f"- Generated at: `{now}`",
        "- Purpose: prove in class that the project is reproducible, queryable, and runnable.",
        "",
        "## Fast Proof Order",
        "",
        "1. Run the local proof: `make -C <project-root> demo-proof`",
        "2. Open the dashboard: `http://127.0.0.1:8000/dashboard` after starting `make serve`.",
        "3. Show API JSON: `/health`, `/metadata`, `/priorities/latest?top_n=5`, `/score`.",
        "4. Show Supabase SQL after live publish: `sql/06_supabase_demo_queries.sql`.",
        "5. Show final audit: `make -C <project-root> final-audit`.",
        "",
        "## What To Say In One Sentence",
        "",
        "I built a real-data decision-support prototype that ranks NYC residential buildings by next-day heating/hot-water complaint risk and explains why each building is prioritized.",
        "",
        "## Core Numbers To Show",
        "",
        f"- Held-out ROC AUC: `{fmt(test.get('roc_auc'))}`",
        f"- Held-out Precision@50: `{fmt(ranking_50.get('mean_precision_at_k'))}`",
        f"- Held-out Lift@50: `{fmt(ranking_50.get('mean_lift_at_k'))}`",
        "- OOT ROC AUC: see out-of-time validation report.",
        "- Dense panel: see data card.",
        "",
        "## Evidence Files",
        "",
        f"- Final audit: [final_project_audit.md]({FINAL_PROJECT_AUDIT_PATH})",
        f"- Demo proof: [demo_proof.md]({DEMO_PROOF_MD})",
        f"- AWS live proof: [aws_live_deploy_proof.md]({AWS_LIVE_DEPLOY_PROOF_MD})",
        f"- AWS shutdown proof: [aws_shutdown_proof.md]({AWS_SHUTDOWN_PROOF_MD})",
        f"- Model card: [model_card.md]({MODEL_CARD_PATH})",
        f"- Data card: [data_card.md]({DATA_CARD_PATH})",
        f"- Dashboard visual summary: [dashboard_summary.png]({EVIDENCE_DASHBOARD_PNG})",
        f"- Supabase readiness: [supabase_readiness.md]({SUPABASE_READINESS_MD})",
        f"- Supabase live checklist: [SUPABASE_LIVE_CHECKLIST.md]({SUPABASE_LIVE_CHECKLIST})",
        f"- Supabase demo SQL: [06_supabase_demo_queries.sql]({SUPABASE_DEMO_SQL})",
        f"- Final slides: [output.pptx]({FINAL_PRESENTATION_DECK_PATH})",
        f"- Record lookup DB: [record_lookup.sqlite]({FINAL_RECORD_LOOKUP_DB_PATH})",
        "",
        "## Honest Status",
        "",
        "- Core analytics and local API proof are ready.",
        "- Supabase is ready as a reporting layer; live publish requires `SUPABASE_DB_URL`.",
        "- AWS has timestamped live proof and shutdown proof; recreate the endpoint only if a currently reachable URL is required on demo day.",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    metadata = read_json(FINAL_MODEL_METADATA_PATH)
    write_model_card(metadata, MODEL_CARD_PATH)
    write_data_card(DATA_CARD_PATH)
    write_dashboard_preview(metadata, EVIDENCE_DASHBOARD_PNG)
    write_evidence_pack(metadata, EVIDENCE_PACK_README)
    print(f"model card written: {MODEL_CARD_PATH}")
    print(f"data card written: {DATA_CARD_PATH}")
    print(f"dashboard visual written: {EVIDENCE_DASHBOARD_PNG}")
    print(f"evidence pack written: {EVIDENCE_PACK_README}")


if __name__ == "__main__":
    main()
