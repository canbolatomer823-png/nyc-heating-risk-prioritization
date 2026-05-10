"""
Minimal training job for the transit delay model.

Designed to run as a Kubernetes Job (or Argo step). It loads processed events,
builds a simple feature set, trains a baseline classifier, and saves artifacts
locally and optionally to S3.
"""

import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import boto3
import joblib
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LATE_THRESHOLD = int(os.environ.get("LATE_THRESHOLD", "120"))


def load_dataset(path: str) -> pd.DataFrame:
    """Load JSON or Parquet events into a DataFrame."""
    if path.endswith(".parquet"):
        df = pd.read_parquet(path)
    else:
        df = pd.read_json(path)
    if "delay_seconds" not in df.columns:
        raise ValueError("Input data must contain delay_seconds field")
    return df


def build_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Create a minimal feature set and target."""
    df = df.copy()
    df["is_late"] = (df["delay_seconds"] > LATE_THRESHOLD).astype(int)
    df["hour"] = pd.to_datetime(df["timestamp"], unit="s").dt.hour
    df["dow"] = pd.to_datetime(df["timestamp"], unit="s").dt.dayofweek

    feature_cols = ["delay_seconds", "hour", "dow"]
    df_cat = pd.get_dummies(df[["route_id", "stop_id"]], drop_first=True)
    X = pd.concat([df[feature_cols], df_cat], axis=1)
    y = df["is_late"]
    return X, y


def train_model(X: pd.DataFrame, y: pd.Series) -> Tuple[GradientBoostingClassifier, Dict[str, float]]:
    min_class_size = y.value_counts().min()
    if len(y) < 5 or min_class_size < 2:
        logger.warning(
            "dataset too small or unbalanced (n=%d, min_class=%d); training on full data without test split",
            len(y),
            min_class_size,
        )
        model = GradientBoostingClassifier(random_state=42)
        model.fit(X, y)
        metrics = {
            "accuracy": None,
            "roc_auc": None,
            "n_samples": int(len(X)),
            "late_threshold_seconds": LATE_THRESHOLD,
            "note": "no_test_split_small_dataset",
        }
        return model, metrics

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model = GradientBoostingClassifier(random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)) if len(y_test.unique()) > 1 else 0.5,
        "n_samples": int(len(X)),
        "late_threshold_seconds": LATE_THRESHOLD,
    }
    return model, metrics


def save_artifacts(model, metrics: Dict[str, float], feature_names, output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    model_path = output_dir / f"model-{timestamp}.joblib"
    metrics_path = output_dir / f"metrics-{timestamp}.json"
    features_path = output_dir / f"features-{timestamp}.json"

    joblib.dump(model, model_path)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    with open(features_path, "w", encoding="utf-8") as f:
        json.dump({"feature_names": list(feature_names)}, f, indent=2)

    logger.info("saved model to %s", model_path)
    logger.info("saved metrics to %s", metrics_path)
    logger.info("saved feature names to %s", features_path)
    return {"model": model_path, "metrics": metrics_path, "features": features_path}


def maybe_upload_to_s3(paths: Dict[str, Path], bucket: str) -> None:
    if not bucket:
        return
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION"))
    prefix = f"models/{datetime.utcnow():%Y/%m/%d}"
    for name, path in paths.items():
        key = f"{prefix}/{path.name}"
        try:
            s3.upload_file(str(path), bucket, key)
            logger.info("uploaded %s to s3://%s/%s", name, bucket, key)
        except (ClientError, BotoCoreError) as e:
            logger.error("failed to upload %s: %s", name, e)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train transit delay model")
    parser.add_argument("--input", required=True, help="Path to JSON events or Parquet file")
    parser.add_argument("--output-dir", default="/tmp/models", help="Local directory for artifacts")
    parser.add_argument("--model-bucket", default=os.environ.get("MODEL_BUCKET", ""), help="Optional S3 bucket for artifacts")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_dataset(args.input)
    X, y = build_features(df)

    if len(df) < 5:
        logger.warning("dataset is very small (%d rows); metrics may be unreliable", len(df))

    model, metrics = train_model(X, y)
    paths = save_artifacts(model, metrics, X.columns, Path(args.output_dir))
    maybe_upload_to_s3(paths, args.model_bucket)


if __name__ == "__main__":
    main()
