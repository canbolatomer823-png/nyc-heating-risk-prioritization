from __future__ import annotations

from pathlib import Path

import pandas as pd


NUMERIC_FEATURES = [
    "complaint_count",
    "unique_request_count",
    "no_heat_count",
    "hot_water_problem_count",
    "lag_1_complaints",
    "rolling_3d_complaints",
    "rolling_7d_complaints",
    "rolling_7d_request_count",
    "complaint_day_count_prior",
    "cumulative_complaints_prior",
    "cumulative_request_count_prior",
    "prior_max_daily_complaints",
    "days_since_last_complaint_capped",
    "registration_active_flag",
    "heat_sensor_program_flag",
    "heat_sensor_active_flag",
    "heat_sensor_unit_count",
    "total_linked_violation_count",
    "open_linked_violation_count",
    "unit_count_proxy",
    "unit_count_effective",
    "open_violation_per_unit",
    "rolling_7d_complaints_per_unit",
    "no_heat_share",
    "hot_water_share",
    "weather_avg_temp_c",
    "weather_max_temp_c",
    "weather_min_temp_c",
    "weather_prcp_mm_mean",
    "weather_prcp_mm_max",
    "weather_wind_mps_mean",
    "weather_heating_degree_c",
    "weather_freezing_any_flag",
    "weather_temp_drop_c",
    "weather_cold_shock_flag",
    "weather_severity_index",
    "cre_coverage_flag",
    "cre_population",
    "cre_pred0_pe",
    "cre_pred3_pe",
    "cre_pred12_pe",
    "cre_vulnerability_index",
    "cre_high_vulnerability_flag",
    "equity_weather_interaction",
]

CATEGORICAL_FEATURES = [
    "borough",
    "management_program",
]

RAW_NUMERIC_DEFAULTS = {
    "complaint_count": 0.0,
    "unique_request_count": 0.0,
    "no_heat_count": 0.0,
    "hot_water_problem_count": 0.0,
    "lag_1_complaints": 0.0,
    "rolling_3d_complaints": 0.0,
    "rolling_7d_complaints": 0.0,
    "rolling_7d_request_count": 0.0,
    "complaint_day_count_prior": 0.0,
    "cumulative_complaints_prior": 0.0,
    "cumulative_request_count_prior": 0.0,
    "prior_max_daily_complaints": 0.0,
    "days_since_last_complaint": 30.0,
    "registration_active_flag": 0.0,
    "heat_sensor_program_flag": 0.0,
    "heat_sensor_active_flag": 0.0,
    "heat_sensor_unit_count": 0.0,
    "total_linked_violation_count": 0.0,
    "open_linked_violation_count": 0.0,
    "unit_count_proxy": 1.0,
    "weather_avg_temp_c": 0.0,
    "weather_max_temp_c": 0.0,
    "weather_min_temp_c": 0.0,
    "weather_prcp_mm_mean": 0.0,
    "weather_prcp_mm_max": 0.0,
    "weather_wind_mps_mean": 0.0,
    "weather_heating_degree_c": 0.0,
    "weather_freezing_any_flag": 0.0,
    "weather_temp_drop_c": 0.0,
    "weather_cold_shock_flag": 0.0,
    "cre_coverage_flag": 0.0,
    "cre_population": 0.0,
    "cre_pred0_pe": 0.0,
    "cre_pred3_pe": 0.0,
    "cre_pred12_pe": 0.0,
    "cre_vulnerability_index": 0.0,
    "cre_high_vulnerability_flag": 0.0,
}

RAW_TEXT_DEFAULTS = {
    "borough": "UNKNOWN",
    "management_program": "unknown",
    "incident_address": "",
    "building_bbl": "",
    "building_id": "",
    "calendar_date": "",
}

MODEL_INPUT_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Keep the logistic benchmark input narrow, but still preserve the
# contextual columns that must survive into the scored output and
# downstream priority/API artifacts.
SCORED_CONTEXT_COLUMNS = [
    "building_id",
    "building_bbl",
    "incident_address",
    "building_zip",
    "community_board",
    "census_tract",
    "surge_flag",
    "weather_station_count",
    "weather_freezing_station_count",
]

MODELING_TABLE_EXTRA_COLUMNS = [
    "next_day_complaint_count",
    "days_since_last_complaint",
    "unit_count_proxy",
    "heat_sensor_unit_count",
]

MODELING_TABLE_COLUMNS = [
    "calendar_date",
    *SCORED_CONTEXT_COLUMNS,
    *MODELING_TABLE_EXTRA_COLUMNS,
    *MODEL_INPUT_COLUMNS,
    "target",
]

LABELED_DATASET_SOURCE_COLUMNS = set(RAW_NUMERIC_DEFAULTS) | set(CATEGORICAL_FEATURES) | {
    "calendar_date",
    "next_day_label_available",
    "next_day_complaint_count",
} | set(SCORED_CONTEXT_COLUMNS)


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for column, default in RAW_NUMERIC_DEFAULTS.items():
        if column not in df.columns:
            df[column] = default
    for column, default in RAW_TEXT_DEFAULTS.items():
        if column not in df.columns:
            df[column] = default
    return df


def prepare_feature_frame(df: pd.DataFrame, compute_target: bool = False) -> pd.DataFrame:
    prepared = ensure_columns(df)
    if "calendar_date" in prepared.columns:
        prepared["calendar_date"] = pd.to_datetime(prepared["calendar_date"], errors="coerce")

    for column in RAW_NUMERIC_DEFAULTS:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(RAW_NUMERIC_DEFAULTS[column])

    prepared["unit_count_effective"] = prepared[["unit_count_proxy", "heat_sensor_unit_count"]].max(axis=1).clip(lower=1)
    prepared["open_violation_per_unit"] = prepared["open_linked_violation_count"] / prepared["unit_count_effective"]
    prepared["rolling_7d_complaints_per_unit"] = prepared["rolling_7d_complaints"] / prepared["unit_count_effective"]
    prepared["days_since_last_complaint_capped"] = prepared["days_since_last_complaint"].where(
        prepared["days_since_last_complaint"] >= 0,
        30,
    ).clip(upper=30)
    prepared["no_heat_share"] = (
        prepared["no_heat_count"] / prepared["complaint_count"].where(prepared["complaint_count"] > 0, 1)
    ).fillna(0)
    prepared["hot_water_share"] = (
        prepared["hot_water_problem_count"] / prepared["complaint_count"].where(prepared["complaint_count"] > 0, 1)
    ).fillna(0)
    prepared["weather_severity_index"] = (
        prepared["weather_heating_degree_c"]
        + prepared["weather_freezing_any_flag"] * 2.0
        + prepared["weather_cold_shock_flag"] * 2.0
        + prepared["weather_temp_drop_c"].clip(lower=0)
    )
    prepared["equity_weather_interaction"] = prepared["cre_vulnerability_index"] * prepared["weather_severity_index"]

    for column in NUMERIC_FEATURES:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    prepared[NUMERIC_FEATURES] = prepared[NUMERIC_FEATURES].fillna(0)

    for column in CATEGORICAL_FEATURES:
        prepared[column] = prepared[column].fillna("unknown").astype(str)

    if compute_target:
        if "next_day_complaint_count" not in prepared.columns:
            raise ValueError("next_day_complaint_count is required when compute_target=True")
        prepared["target"] = (pd.to_numeric(prepared["next_day_complaint_count"], errors="coerce").fillna(0) >= 1).astype(int)

    return prepared


def load_labeled_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        low_memory=False,
        usecols=lambda column: column in LABELED_DATASET_SOURCE_COLUMNS,
    )
    if "next_day_label_available" not in df.columns:
        raise ValueError("Expected next_day_label_available in dense panel.")
    df = df[df["next_day_label_available"] == 1].copy()
    return prepare_feature_frame(df, compute_target=True)


def load_prepared_modeling_table(
    path: Path,
    columns: list[str] | None = None,
    allowed_dates: set[str] | None = None,
    chunksize: int = 250_000,
) -> pd.DataFrame:
    selected_columns = columns or MODELING_TABLE_COLUMNS
    frames: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        path,
        low_memory=False,
        usecols=lambda column: column in selected_columns,
        chunksize=chunksize,
    ):
        if "calendar_date" in chunk.columns:
            chunk["calendar_date"] = pd.to_datetime(chunk["calendar_date"], errors="coerce")
            if allowed_dates is not None:
                chunk = chunk[chunk["calendar_date"].dt.strftime("%Y-%m-%d").isin(allowed_dates)]
        if not chunk.empty:
            frames.append(chunk)

    if not frames:
        return pd.DataFrame(columns=selected_columns)
    return pd.concat(frames, ignore_index=True)
