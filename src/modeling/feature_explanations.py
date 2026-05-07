from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from modeling.risk_features import CATEGORICAL_FEATURES, MODEL_INPUT_COLUMNS, prepare_feature_frame


READABLE_FEATURE_LABELS = {
    "complaint_count": "same-day complaints",
    "unique_request_count": "unique requests",
    "no_heat_count": "no-heat complaints",
    "hot_water_problem_count": "hot-water complaints",
    "lag_1_complaints": "yesterday complaints",
    "rolling_3d_complaints": "3-day complaint history",
    "rolling_7d_complaints": "7-day complaint history",
    "complaint_day_count_prior": "prior complaint days",
    "cumulative_complaints_prior": "cumulative complaint history",
    "prior_max_daily_complaints": "prior max daily complaints",
    "days_since_last_complaint_capped": "recent complaint recency",
    "heat_sensor_active_flag": "active heat sensor flag",
    "open_linked_violation_count": "open HPD violations",
    "open_violation_per_unit": "open violations per unit",
    "rolling_7d_complaints_per_unit": "7-day complaints per unit",
    "weather_avg_temp_c": "average temperature",
    "weather_max_temp_c": "maximum temperature",
    "weather_min_temp_c": "minimum temperature",
    "weather_prcp_mm_mean": "average precipitation",
    "weather_prcp_mm_max": "maximum precipitation",
    "weather_wind_mps_mean": "wind speed",
    "weather_heating_degree_c": "cold weather load",
    "weather_freezing_any_flag": "freezing weather flag",
    "weather_temp_drop_c": "temperature drop",
    "weather_cold_shock_flag": "cold shock flag",
    "weather_severity_index": "weather severity",
    "cre_vulnerability_index": "CRE vulnerability",
    "cre_high_vulnerability_flag": "high CRE vulnerability flag",
    "equity_weather_interaction": "CRE x weather interaction",
    "unit_count_effective": "building unit scale",
    "borough": "borough",
    "management_program": "management program",
}


def source_feature_name(feature_name: str) -> tuple[str, str | None]:
    clean = feature_name
    if clean.startswith("num__"):
        return clean.removeprefix("num__"), None
    if clean.startswith("cat__"):
        remainder = clean.removeprefix("cat__")
        for column in CATEGORICAL_FEATURES:
            prefix = f"{column}_"
            if remainder.startswith(prefix):
                return column, remainder.removeprefix(prefix)
        return remainder, None
    return clean, None


def readable_feature_name(feature_name: str) -> str:
    source, category = source_feature_name(feature_name)
    label = READABLE_FEATURE_LABELS.get(source, source.replace("_", " "))
    if category is not None:
        return f"{label} = {category}"
    return label


def raw_value_for(row: pd.Series, feature_name: str) -> Any:
    source, category = source_feature_name(feature_name)
    if category is not None:
        return category
    value = row.get(source)
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def format_raw_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def is_zero_like(value: Any) -> bool:
    try:
        return abs(float(value)) < 1e-12
    except Exception:
        return False


def contributor_record(feature_name: str, contribution: float, row: pd.Series) -> dict[str, Any]:
    return {
        "feature": feature_name,
        "label": readable_feature_name(feature_name),
        "raw_value": raw_value_for(row, feature_name),
        "contribution": round(float(contribution), 4),
    }


def build_reason_sentence(positive_contributors: list[dict[str, Any]], max_reasons: int = 3) -> str:
    if not positive_contributors:
        return "Risk score is driven by the calibrated model and equity-weighted ranking; no single positive driver dominates."
    concrete = [item for item in positive_contributors if not is_zero_like(item.get("raw_value"))]
    selected = concrete if concrete else positive_contributors
    fragments = []
    for item in selected[:max_reasons]:
        raw = format_raw_value(item.get("raw_value"))
        fragments.append(f"{item['label']}={raw}")
    return "Riski yukselten baslica sinyaller: " + ", ".join(fragments) + "."


def format_contributor_list(contributors: list[dict[str, Any]]) -> str:
    return "; ".join(
        f"{item['label']}={format_raw_value(item.get('raw_value'))} ({item['contribution']:+.4f})"
        for item in contributors
    )


def explain_model_rows(
    model: Any,
    metadata: dict[str, Any],
    rows: list[dict[str, Any]],
    top_n: int = 5,
) -> list[dict[str, Any]]:
    if not rows:
        return []

    frame = prepare_feature_frame(pd.DataFrame(rows), compute_target=False)
    transformed = model.named_steps["preprocess"].transform(frame[MODEL_INPUT_COLUMNS])
    transformed_values = transformed.toarray() if hasattr(transformed, "toarray") else np.asarray(transformed)
    feature_names = metadata.get("feature_names") or model.named_steps["preprocess"].get_feature_names_out().tolist()
    coefficients = model.named_steps["classifier"].coef_[0]

    explanations: list[dict[str, Any]] = []
    for row_index in range(len(frame)):
        contributions = transformed_values[row_index] * coefficients
        ranked = sorted(zip(feature_names, contributions), key=lambda item: item[1], reverse=True)
        row = frame.iloc[row_index]
        positive = [
            contributor_record(name, value, row)
            for name, value in ranked
            if value > 0
        ][:top_n]
        negative = [
            contributor_record(name, value, row)
            for name, value in ranked[::-1]
            if value < 0
        ][:top_n]
        explanations.append(
            {
                "why_risky": build_reason_sentence(positive),
                "top_positive_contributors": positive,
                "top_negative_contributors": negative,
                "top_positive_contributors_text": format_contributor_list(positive),
                "top_negative_contributors_text": format_contributor_list(negative),
            }
        )
    return explanations
