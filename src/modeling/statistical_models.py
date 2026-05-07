from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from patsy import build_design_matrices
from scipy.special import expit
from scipy.stats import norm
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, recall_score
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
from statsmodels.genmod.cov_struct import Exchangeable

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import (
    FINAL_DENSE_PANEL_PATH,
    FINAL_MODELING_TABLE_PATH,
    FINAL_STATISTICAL_COEFFICIENTS_PATH,
    FINAL_STATISTICAL_METRICS_PATH,
)

GEE_FORMULA_TERMS = [
    "log1p_current_complaint_count",
    "log1p_rolling_3d_complaints",
    "log1p_complaint_day_count_prior",
    "log_prior_complaints",
    "log1p_prior_max_daily_complaints",
    "log_open_violations",
    "heat_sensor_active_flag",
    "log_units",
    "weather_heating_degree_scaled",
    "weather_temp_drop_c",
    "weather_prcp_mm_mean",
    "cre_vulnerability_index",
    "equity_weather_interaction_scaled",
    "recent_complaint_flag",
    "C(borough)",
]

NB_FORMULA_TERMS = [
    "log1p_current_complaint_count",
    "log1p_rolling_3d_complaints",
    "log1p_complaint_day_count_prior",
    "log_prior_complaints",
    "log1p_prior_max_daily_complaints",
    "log_open_violations",
    "heat_sensor_active_flag",
    "log_units",
    "weather_heating_degree_scaled",
    "weather_temp_drop_c",
    "weather_prcp_mm_mean",
    "cre_vulnerability_index",
    "cre_high_vulnerability_flag",
    "equity_weather_interaction",
    "recent_complaint_flag",
    "C(borough)",
]

GLMM_FORMULA_TERMS = [
    "log1p_current_complaint_count",
    "log1p_complaint_day_count_prior",
    "log_open_violations",
    "heat_sensor_active_flag",
    "weather_heating_degree_scaled",
    "weather_temp_drop_c",
    "weather_prcp_mm_mean",
    "cre_vulnerability_index",
    "equity_weather_interaction_scaled",
    "recent_complaint_flag",
    "C(borough)",
]

STATISTICAL_SOURCE_COLUMNS = {
    "building_id",
    "calendar_date",
    "next_day_label_available",
    "next_day_complaint_count",
    "complaint_count",
    "rolling_3d_complaints",
    "complaint_day_count_prior",
    "cumulative_complaints_prior",
    "prior_max_daily_complaints",
    "days_since_last_complaint",
    "open_linked_violation_count",
    "unit_count_proxy",
    "heat_sensor_unit_count",
    "heat_sensor_active_flag",
    "weather_heating_degree_c",
    "weather_temp_drop_c",
    "weather_prcp_mm_mean",
    "weather_freezing_any_flag",
    "weather_cold_shock_flag",
    "cre_vulnerability_index",
    "cre_high_vulnerability_flag",
    "borough",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit inference-oriented statistical models for NYC heat-risk.")
    parser.add_argument(
        "--input",
        default=str(FINAL_MODELING_TABLE_PATH),
        help="Prepared modeling table CSV path. Falls back to the dense panel if needed.",
    )
    parser.add_argument(
        "--metrics-output",
        default=str(FINAL_STATISTICAL_METRICS_PATH),
        help="Markdown summary output path.",
    )
    parser.add_argument(
        "--coefficients-output",
        default=str(FINAL_STATISTICAL_COEFFICIENTS_PATH),
        help="CSV output path for model coefficients.",
    )
    parser.add_argument(
        "--max-train-rows",
        type=int,
        default=50000,
        help="Maximum sampled rows for train split in full-window inference runs.",
    )
    parser.add_argument(
        "--max-validation-rows",
        type=int,
        default=25000,
        help="Maximum sampled rows for validation split in full-window inference runs.",
    )
    parser.add_argument(
        "--max-test-rows",
        type=int,
        default=25000,
        help="Maximum sampled rows for test split in full-window inference runs.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducible split sampling.",
    )
    parser.add_argument(
        "--max-glmm-train-rows",
        type=int,
        default=5000,
        help="Maximum stratified train rows used for the GLMM fit.",
    )
    parser.add_argument(
        "--max-glmm-validation-rows",
        type=int,
        default=2500,
        help="Maximum stratified validation rows used for GLMM threshold selection.",
    )
    parser.add_argument(
        "--max-glmm-test-rows",
        type=int,
        default=2500,
        help="Maximum stratified test rows used for GLMM held-out evaluation.",
    )
    parser.add_argument(
        "--glmm-max-iter",
        type=int,
        default=400,
        help="Maximum optimizer iterations for the variational Bayes GLMM fit.",
    )
    return parser.parse_args()


def prepare_dataset(path: Path) -> pd.DataFrame:
    source_path = path if path.exists() else FINAL_DENSE_PANEL_PATH
    df = pd.read_csv(
        source_path,
        low_memory=False,
        usecols=lambda column: column in STATISTICAL_SOURCE_COLUMNS,
    )
    df["calendar_date"] = pd.to_datetime(df["calendar_date"], errors="coerce")
    if "next_day_label_available" in df.columns:
        df = df[df["next_day_label_available"] == 1].copy()
    else:
        df = df.copy()
    df["building_id"] = df["building_id"].astype(str)
    df["next_day_positive_flag"] = (df["next_day_complaint_count"] >= 1).astype(int)
    df["unit_count_effective"] = df[["unit_count_proxy", "heat_sensor_unit_count"]].max(axis=1).clip(lower=1)
    df["log_open_violations"] = np.log1p(df["open_linked_violation_count"].clip(lower=0))
    df["log_prior_complaints"] = np.log1p(df["cumulative_complaints_prior"].clip(lower=0))
    df["log_units"] = np.log1p(df["unit_count_effective"])
    df["log1p_current_complaint_count"] = np.log1p(df["complaint_count"].clip(lower=0))
    df["log1p_rolling_3d_complaints"] = np.log1p(df["rolling_3d_complaints"].clip(lower=0))
    df["log1p_complaint_day_count_prior"] = np.log1p(df["complaint_day_count_prior"].clip(lower=0))
    df["log1p_prior_max_daily_complaints"] = np.log1p(df["prior_max_daily_complaints"].clip(lower=0))
    df["recent_complaint_flag"] = (df["days_since_last_complaint"].fillna(99).clip(lower=-1) <= 2).astype(int)
    df["weather_temp_drop_c"] = df["weather_temp_drop_c"].fillna(0)
    df["weather_prcp_mm_mean"] = df["weather_prcp_mm_mean"].fillna(0)
    df["cre_vulnerability_index"] = pd.to_numeric(df.get("cre_vulnerability_index", 0), errors="coerce").fillna(0)
    df["cre_high_vulnerability_flag"] = pd.to_numeric(df.get("cre_high_vulnerability_flag", 0), errors="coerce").fillna(0)
    df["weather_heating_degree_scaled"] = df["weather_heating_degree_c"] / 10.0
    df["weather_severity_index"] = (
        df["weather_heating_degree_c"].fillna(0)
        + df["weather_temp_drop_c"].clip(lower=0)
        + (df["weather_freezing_any_flag"].fillna(0) * 2.0)
        + (df["weather_cold_shock_flag"].fillna(0) * 2.0)
    )
    df["equity_weather_interaction"] = df["cre_vulnerability_index"] * df["weather_severity_index"]
    df["equity_weather_interaction_scaled"] = df["equity_weather_interaction"] / 10.0
    return df


def split_by_date(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    unique_dates = sorted(df["calendar_date"].dropna().dt.strftime("%Y-%m-%d").unique())
    if len(unique_dates) < 6:
        raise ValueError("Need at least 6 labeled dates for train/validation/test splits.")

    train_cut = max(1, int(len(unique_dates) * 0.6))
    val_cut = min(max(train_cut + 1, int(len(unique_dates) * 0.8)), len(unique_dates) - 1)

    train_dates = set(unique_dates[:train_cut])
    val_dates = set(unique_dates[train_cut:val_cut])
    test_dates = set(unique_dates[val_cut:])

    key_dates = df["calendar_date"].dt.strftime("%Y-%m-%d")
    train_df = df[key_dates.isin(train_dates)].copy()
    val_df = df[key_dates.isin(val_dates)].copy()
    test_df = df[key_dates.isin(test_dates)].copy()
    return train_df, val_df, test_df


def stratified_sample(df: pd.DataFrame, max_rows: int, random_state: int) -> pd.DataFrame:
    if max_rows <= 0 or len(df) <= max_rows:
        return df.copy()

    positives = df[df["next_day_positive_flag"] == 1]
    negatives = df[df["next_day_positive_flag"] == 0]

    if positives.empty or negatives.empty:
        return df.sample(n=max_rows, random_state=random_state).copy()

    positive_quota = min(len(positives), max(1, int(round(max_rows * float(positives.shape[0] / len(df))))))
    negative_quota = max_rows - positive_quota

    sampled_positive = positives.sample(n=positive_quota, random_state=random_state, replace=False)
    sampled_negative = negatives.sample(n=min(len(negatives), negative_quota), random_state=random_state, replace=False)
    sampled = pd.concat([sampled_positive, sampled_negative], axis=0)
    if len(sampled) < max_rows:
        remaining = df.loc[~df.index.isin(sampled.index)]
        needed = min(len(remaining), max_rows - len(sampled))
        if needed > 0:
            sampled = pd.concat(
                [sampled, remaining.sample(n=needed, random_state=random_state, replace=False)],
                axis=0,
            )
    return sampled.sample(frac=1.0, random_state=random_state).reset_index(drop=True)


def select_threshold(y_true: pd.Series, probabilities: pd.Series) -> float:
    best_threshold = 0.5
    best_score: tuple[float, float, float] | None = None
    for raw in range(10, 91, 5):
        threshold = raw / 100
        predictions = (probabilities >= threshold).astype(int)
        precision = precision_score(y_true, predictions, zero_division=0)
        recall = recall_score(y_true, predictions, zero_division=0)
        f1 = f1_score(y_true, predictions, zero_division=0)
        score = (f1, recall, precision)
        if best_score is None or score > best_score:
            best_threshold = threshold
            best_score = score
    return best_threshold


def classification_metrics(y_true: pd.Series, probabilities: pd.Series, threshold: float) -> dict[str, float]:
    predictions = (probabilities >= threshold).astype(int)
    return {
        "rows": float(len(y_true)),
        "actual_positive_rate": float(y_true.mean()),
        "predicted_positive_rate": float(predictions.mean()),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
    }


def count_metrics(y_true: pd.Series, predictions: pd.Series) -> dict[str, float]:
    return {
        "rows": float(len(y_true)),
        "mean_actual_count": float(y_true.mean()),
        "mean_predicted_count": float(predictions.mean()),
        "mae": float(mean_absolute_error(y_true, predictions)),
        "rmse": float(mean_squared_error(y_true, predictions, squared=False)),
    }


def fit_models(train_df: pd.DataFrame, val_df: pd.DataFrame):
    gee_formula = f"next_day_positive_flag ~ {' + '.join(GEE_FORMULA_TERMS)}"
    nb_formula = f"next_day_complaint_count ~ {' + '.join(NB_FORMULA_TERMS)}"

    gee_model = smf.gee(
        gee_formula,
        groups="building_id",
        data=train_df,
        family=sm.families.Binomial(),
        cov_struct=Exchangeable(),
    )
    gee_result = gee_model.fit(maxiter=100, cov_type="robust")
    if not np.isfinite(np.asarray(gee_result.params)).all():
        raise ValueError("GEE fit returned non-finite parameters.")

    val_probabilities = pd.Series(gee_result.predict(val_df), index=val_df.index)
    threshold = select_threshold(val_df["next_day_positive_flag"], val_probabilities)

    mean_count = float(train_df["next_day_complaint_count"].mean())
    var_count = float(train_df["next_day_complaint_count"].var())
    alpha = max((var_count - mean_count) / max(mean_count**2, 1e-6), 0.1)

    nb_model = smf.glm(
        nb_formula,
        data=train_df,
        family=sm.families.NegativeBinomial(alpha=alpha),
    )
    nb_result = nb_model.fit(maxiter=100)
    return gee_result, nb_result, threshold


def sample_glmm_splits(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    max_train_rows: int,
    max_validation_rows: int,
    max_test_rows: int,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    building_targets = (
        train_df.groupby("building_id", observed=True)["next_day_positive_flag"]
        .max()
        .reset_index()
    )
    max_buildings = min(len(building_targets), max(80, max_train_rows // 12))
    positive_buildings = building_targets[building_targets["next_day_positive_flag"] > 0]
    negative_buildings = building_targets[building_targets["next_day_positive_flag"] <= 0]
    positive_count = min(len(positive_buildings), max(20, max_buildings // 3))
    negative_count = max(0, max_buildings - positive_count)
    selected_buildings = pd.concat(
        [
            positive_buildings.sample(n=positive_count, random_state=random_state, replace=False)
            if positive_count
            else positive_buildings,
            negative_buildings.sample(n=min(len(negative_buildings), negative_count), random_state=random_state + 1, replace=False)
            if negative_count
            else negative_buildings.iloc[0:0],
        ],
        ignore_index=True,
    )["building_id"]
    selected_ids = set(selected_buildings.astype(str))

    def filter_and_sample(frame: pd.DataFrame, max_rows: int, seed: int) -> pd.DataFrame:
        subset = frame[frame["building_id"].astype(str).isin(selected_ids)].copy()
        return stratified_sample(subset, max_rows, seed)

    glmm_train_df = filter_and_sample(train_df, max_train_rows, random_state + 10)
    glmm_val_df = filter_and_sample(val_df, max_validation_rows, random_state + 101)
    glmm_test_df = filter_and_sample(test_df, max_test_rows, random_state + 202)
    return glmm_train_df, glmm_val_df, glmm_test_df


def shared_building_stats(train_df: pd.DataFrame, eval_df: pd.DataFrame) -> dict[str, float]:
    train_buildings = set(train_df["building_id"].astype(str))
    eval_buildings = eval_df["building_id"].astype(str)
    shared_mask = eval_buildings.isin(train_buildings)
    return {
        "shared_rows": float(shared_mask.sum()),
        "shared_row_rate": float(shared_mask.mean()) if len(shared_mask) else 0.0,
        "shared_buildings": float(eval_buildings[shared_mask].nunique()),
        "eval_unique_buildings": float(eval_buildings.nunique()),
    }


def parse_vc_name(name: str) -> str:
    match = re.search(r"\[(.*?)\]$", name)
    if not match:
        return name
    value = match.group(1)
    if value.startswith("T."):
        value = value[2:]
    return value


def fit_glmm(train_df: pd.DataFrame, val_df: pd.DataFrame, maxiter: int):
    glmm_formula = f"next_day_positive_flag ~ {' + '.join(GLMM_FORMULA_TERMS)}"
    glmm_model = BinomialBayesMixedGLM.from_formula(
        glmm_formula,
        {"building_re": "0 + C(building_id)"},
        train_df,
    )
    glmm_result = glmm_model.fit_vb(
        fit_method="BFGS",
        minim_opts={"maxiter": maxiter},
        scale_fe=True,
        verbose=False,
    )
    val_probabilities = glmm_predict(glmm_model, glmm_result, val_df)
    threshold = select_threshold(val_df["next_day_positive_flag"], val_probabilities)
    return glmm_model, glmm_result, threshold


def glmm_predict(model: BinomialBayesMixedGLM, result, df: pd.DataFrame) -> pd.Series:
    fixed_exog = build_design_matrices([model.data.design_info], df, return_type="dataframe")[0]
    random_effect_lookup = {
        parse_vc_name(name): float(value)
        for name, value in zip(model.vc_names, result.vc_mean)
    }
    building_random = df["building_id"].astype(str).map(random_effect_lookup).fillna(0.0).to_numpy()
    linear_predictor = fixed_exog.to_numpy() @ result.fe_mean + building_random
    return pd.Series(expit(linear_predictor), index=df.index)


def coefficient_frame(model_name: str, result, transform: str) -> pd.DataFrame:
    params = result.params
    conf_int = result.conf_int()
    pvalues = result.pvalues
    frame = pd.DataFrame(
        {
            "model": model_name,
            "term": params.index,
            "coefficient": params.values,
            "p_value": pvalues.values,
            "conf_low": conf_int[0].values,
            "conf_high": conf_int[1].values,
        }
    )
    if transform == "odds_ratio":
        frame["effect"] = np.exp(frame["coefficient"])
    elif transform == "irr":
        frame["effect"] = np.exp(frame["coefficient"])
    else:
        frame["effect"] = np.nan
    return frame.sort_values(["model", "p_value", "coefficient"], ascending=[True, True, False])


def glmm_coefficient_frame(model_name: str, model: BinomialBayesMixedGLM, result) -> pd.DataFrame:
    coefficient = np.asarray(result.fe_mean, dtype=float)
    sd = np.asarray(result.fe_sd, dtype=float)
    z_value = np.divide(coefficient, sd, out=np.zeros_like(coefficient), where=sd > 0)
    p_value = 2 * norm.sf(np.abs(z_value))
    conf_low = coefficient - 1.96 * sd
    conf_high = coefficient + 1.96 * sd
    frame = pd.DataFrame(
        {
            "model": model_name,
            "term": model.exog_names,
            "coefficient": coefficient,
            "p_value": p_value,
            "conf_low": conf_low,
            "conf_high": conf_high,
            "effect": np.exp(coefficient),
            "posterior_sd": sd,
        }
    )
    random_sd = float(np.exp(result.vcp_mean[0])) if len(result.vcp_mean) else np.nan
    variance_row = pd.DataFrame(
        [
            {
                "model": model_name,
                "term": "sd_building_random_intercept",
                "coefficient": float(result.vcp_mean[0]) if len(result.vcp_mean) else np.nan,
                "p_value": np.nan,
                "conf_low": np.nan,
                "conf_high": np.nan,
                "effect": random_sd,
                "posterior_sd": float(result.vcp_sd[0]) if len(result.vcp_sd) else np.nan,
            }
        ]
    )
    return pd.concat([frame, variance_row], ignore_index=True).sort_values(
        ["model", "p_value", "coefficient"], ascending=[True, True, False], na_position="last"
    )


def top_significant_terms(frame: pd.DataFrame, limit: int = 8) -> pd.DataFrame:
    return frame[frame["term"] != "Intercept"].sort_values(["p_value", "coefficient"], ascending=[True, False]).head(limit)


def format_metric_block(title: str, metrics: dict[str, float], date_min: str, date_max: str) -> list[str]:
    lines = [
        f"## {title}",
        f"- Date range: {date_min} -> {date_max}",
    ]
    for key, value in metrics.items():
        if key == "rows":
            lines.append(f"- {key}: {int(value)}")
        else:
            lines.append(f"- {key}: {round(value, 4)}")
    lines.append("")
    return lines


def main() -> None:
    args = parse_args()
    print("phase=prepare_dataset", flush=True)
    df = prepare_dataset(Path(args.input))
    print("phase=split_and_sample", flush=True)
    train_df, val_df, test_df = split_by_date(df)
    train_fit_df = stratified_sample(train_df, args.max_train_rows, args.random_state)
    val_fit_df = stratified_sample(val_df, args.max_validation_rows, args.random_state + 1)
    test_fit_df = stratified_sample(test_df, args.max_test_rows, args.random_state + 2)

    print("phase=fit_gee_and_negative_binomial", flush=True)
    gee_result, nb_result, threshold = fit_models(train_fit_df, val_fit_df)
    print("phase=sample_glmm_splits", flush=True)
    glmm_train_df, glmm_val_df, glmm_test_df = sample_glmm_splits(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        max_train_rows=args.max_glmm_train_rows,
        max_validation_rows=args.max_glmm_validation_rows,
        max_test_rows=args.max_glmm_test_rows,
        random_state=args.random_state + 500,
    )
    print("phase=fit_glmm", flush=True)
    glmm_model, glmm_result, glmm_threshold = fit_glmm(glmm_train_df, glmm_val_df, args.glmm_max_iter)
    glmm_val_shared = shared_building_stats(glmm_train_df, glmm_val_df)
    glmm_test_shared = shared_building_stats(glmm_train_df, glmm_test_df)

    print("phase=evaluate_models", flush=True)
    train_prob = pd.Series(gee_result.predict(train_fit_df), index=train_fit_df.index)
    val_prob = pd.Series(gee_result.predict(val_fit_df), index=val_fit_df.index)
    test_prob = pd.Series(gee_result.predict(test_fit_df), index=test_fit_df.index)
    glmm_train_prob = glmm_predict(glmm_model, glmm_result, glmm_train_df)
    glmm_val_prob = glmm_predict(glmm_model, glmm_result, glmm_val_df)
    glmm_test_prob = glmm_predict(glmm_model, glmm_result, glmm_test_df)

    train_cls = classification_metrics(train_fit_df["next_day_positive_flag"], train_prob, threshold)
    val_cls = classification_metrics(val_fit_df["next_day_positive_flag"], val_prob, threshold)
    test_cls = classification_metrics(test_fit_df["next_day_positive_flag"], test_prob, threshold)
    glmm_train_cls = classification_metrics(glmm_train_df["next_day_positive_flag"], glmm_train_prob, glmm_threshold)
    glmm_val_cls = classification_metrics(glmm_val_df["next_day_positive_flag"], glmm_val_prob, glmm_threshold)
    glmm_test_cls = classification_metrics(glmm_test_df["next_day_positive_flag"], glmm_test_prob, glmm_threshold)

    train_nb_pred = pd.Series(nb_result.predict(train_fit_df).clip(lower=0), index=train_fit_df.index)
    val_nb_pred = pd.Series(nb_result.predict(val_fit_df).clip(lower=0), index=val_fit_df.index)
    test_nb_pred = pd.Series(nb_result.predict(test_fit_df).clip(lower=0), index=test_fit_df.index)

    train_count = count_metrics(train_fit_df["next_day_complaint_count"], train_nb_pred)
    val_count = count_metrics(val_fit_df["next_day_complaint_count"], val_nb_pred)
    test_count = count_metrics(test_fit_df["next_day_complaint_count"], test_nb_pred)

    gee_coeffs = coefficient_frame("gee_logistic", gee_result, "odds_ratio")
    nb_coeffs = coefficient_frame("negative_binomial", nb_result, "irr")
    glmm_coeffs = glmm_coefficient_frame("binomial_glmm", glmm_model, glmm_result)
    coefficients = pd.concat([gee_coeffs, nb_coeffs, glmm_coeffs], ignore_index=True)
    print("phase=write_outputs", flush=True)
    coefficients.to_csv(args.coefficients_output, index=False)

    gee_top = top_significant_terms(gee_coeffs)
    nb_top = top_significant_terms(nb_coeffs)
    glmm_top = top_significant_terms(glmm_coeffs[glmm_coeffs["term"] != "sd_building_random_intercept"])
    glmm_optim = getattr(glmm_result, "optim_retvals", {}) or {}
    glmm_converged = bool(glmm_optim.get("success", False)) if hasattr(glmm_optim, "get") else False

    lines = [
        "# Statistical Model Metrics",
        "",
        "## Setup",
        f"- GEE threshold selected on validation split: {round(threshold, 4)}",
        f"- Binomial GLMM threshold selected on validation split: {round(glmm_threshold, 4)}",
        f"- GEE formula terms: {', '.join(GEE_FORMULA_TERMS)}",
        f"- GLMM formula terms: {', '.join(GLMM_FORMULA_TERMS)}",
        f"- NB formula terms: {', '.join(NB_FORMULA_TERMS)}",
        f"- Full train rows: {len(train_df)}",
        f"- Full validation rows: {len(val_df)}",
        f"- Full test rows: {len(test_df)}",
        f"- Sampled train rows: {len(train_fit_df)}",
        f"- Sampled validation rows: {len(val_fit_df)}",
        f"- Sampled test rows: {len(test_fit_df)}",
        f"- GLMM sampled train rows: {len(glmm_train_df)}",
        f"- GLMM sampled validation rows: {len(glmm_val_df)}",
        f"- GLMM sampled test rows: {len(glmm_test_df)}",
        f"- GLMM unique buildings: {glmm_train_df['building_id'].nunique()}",
        f"- GLMM validation shared-row rate: {round(glmm_val_shared['shared_row_rate'], 4)}",
        f"- GLMM test shared-row rate: {round(glmm_test_shared['shared_row_rate'], 4)}",
        "",
        "## GEE Logistic",
        f"- Covariance structure: Exchangeable",
        f"- Cluster variable: building_id",
        f"- Inference is fit on stratified split samples for tractable full-window estimation.",
        "",
    ]
    lines.extend(format_metric_block("GEE Train", train_cls, str(train_fit_df['calendar_date'].min())[:10], str(train_fit_df['calendar_date'].max())[:10]))
    lines.extend(format_metric_block("GEE Validation", val_cls, str(val_fit_df['calendar_date'].min())[:10], str(val_fit_df['calendar_date'].max())[:10]))
    lines.extend(format_metric_block("GEE Test", test_cls, str(test_fit_df['calendar_date'].min())[:10], str(test_fit_df['calendar_date'].max())[:10]))
    lines.extend(
        [
            "## Binomial GLMM",
            f"- Random effect: building_id random intercept",
            f"- Fit method: variational Bayes",
            f"- Optimizer converged: {str(glmm_converged).lower()}",
            f"- Approximate random-intercept SD: {round(float(np.exp(glmm_result.vcp_mean[0])), 4)}",
            f"- Fit uses a building-panel stratified sample drawn from the full date-based splits so each sampled building contributes repeated rows.",
            f"- Validation/test evaluation uses the same sampled building panel to evaluate the random-intercept structure.",
            "",
        ]
    )
    lines.extend(format_metric_block("GLMM Train", glmm_train_cls, str(glmm_train_df['calendar_date'].min())[:10], str(glmm_train_df['calendar_date'].max())[:10]))
    lines.extend(format_metric_block("GLMM Validation", glmm_val_cls, str(glmm_val_df['calendar_date'].min())[:10], str(glmm_val_df['calendar_date'].max())[:10]))
    lines.extend(format_metric_block("GLMM Test", glmm_test_cls, str(glmm_test_df['calendar_date'].min())[:10], str(glmm_test_df['calendar_date'].max())[:10]))

    lines.extend(
        [
            "## Negative Binomial Count Model",
            f"- Train AIC: {round(float(nb_result.aic), 4)}",
            f"- Validation pseudo-metrics use held-out prediction only",
            "",
        ]
    )
    lines.extend(format_metric_block("NB Train", train_count, str(train_fit_df['calendar_date'].min())[:10], str(train_fit_df['calendar_date'].max())[:10]))
    lines.extend(format_metric_block("NB Validation", val_count, str(val_fit_df['calendar_date'].min())[:10], str(val_fit_df['calendar_date'].max())[:10]))
    lines.extend(format_metric_block("NB Test", test_count, str(test_fit_df['calendar_date'].min())[:10], str(test_fit_df['calendar_date'].max())[:10]))

    lines.append("## Top Significant GEE Terms")
    for row in gee_top.itertuples(index=False):
        lines.append(
            f"- {row.term}: coef={round(float(row.coefficient), 4)}, effect={round(float(row.effect), 4)}, p={round(float(row.p_value), 6)}"
        )
    lines.append("")
    lines.append("## Top Significant GLMM Terms")
    for row in glmm_top.itertuples(index=False):
        lines.append(
            f"- {row.term}: coef={round(float(row.coefficient), 4)}, effect={round(float(row.effect), 4)}, p={round(float(row.p_value), 6)}"
        )
    lines.append("")
    lines.append("## Top Significant Negative Binomial Terms")
    for row in nb_top.itertuples(index=False):
        lines.append(
            f"- {row.term}: coef={round(float(row.coefficient), 4)}, effect={round(float(row.effect), 4)}, p={round(float(row.p_value), 6)}"
        )
    lines.append("")
    lines.append("GEE gives clustered marginal inference, Binomial GLMM is retained as a building-panel mixed-effects diagnostic with an explicit convergence note, and Negative Binomial gives count-oriented inference for next-day complaint volume.")

    metrics_path = Path(args.metrics_output)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote metrics to {args.metrics_output}", flush=True)
    print(f"wrote coefficients to {args.coefficients_output}", flush=True)


if __name__ == "__main__":
    main()
