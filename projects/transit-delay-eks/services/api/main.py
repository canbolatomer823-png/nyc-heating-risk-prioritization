"""
FastAPI service for transit delay predictions.

It expects a trained sklearn model + feature_names JSON (created by services/train/train.py).
You can point to local artifacts (MODEL_PATH, FEATURE_PATH) or let it download from S3
using MODEL_BUCKET + MODEL_KEY (+ FEATURE_KEY).

If nothing is provided, the service will train a tiny bootstrap model from the sample
events so that /predict works out of the box for demos.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

import boto3
import joblib
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LATE_THRESHOLD = int(os.environ.get("LATE_THRESHOLD", "120"))

MODEL_BUCKET = os.environ.get("MODEL_BUCKET")
MODEL_KEY = os.environ.get("MODEL_KEY")
FEATURE_KEY = os.environ.get("FEATURE_KEY")
MODEL_PATH = os.environ.get("MODEL_PATH")
FEATURE_PATH = os.environ.get("FEATURE_PATH")

app = FastAPI(title="Transit Delay Predictor", version="0.1.0")

model = None
feature_names: List[str] = []
model_source: str = "bootstrap"


class PredictRequest(BaseModel):
    route_id: str
    stop_id: str
    timestamp: int
    delay_seconds: int


class PredictResponse(BaseModel):
    late_probability: float
    is_late: bool
    model_source: str
    threshold_seconds: int


def _feature_frame(payload: PredictRequest, columns: List[str]) -> pd.DataFrame:
    df = pd.DataFrame(
        [
            {
                "route_id": payload.route_id,
                "stop_id": payload.stop_id,
                "delay_seconds": payload.delay_seconds,
                "timestamp": payload.timestamp,
            }
        ]
    )
    df["hour"] = pd.to_datetime(df["timestamp"], unit="s").dt.hour
    df["dow"] = pd.to_datetime(df["timestamp"], unit="s").dt.dayofweek

    df_cat = pd.get_dummies(df[["route_id", "stop_id"]], drop_first=True)
    X = pd.concat([df[["delay_seconds", "hour", "dow"]], df_cat], axis=1)
    X = X.reindex(columns=columns, fill_value=0)
    return X


def _load_feature_names(path: Path) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("feature_names", [])


def _download_from_s3(bucket: str, key: str, dest: Path) -> Path:
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("downloading s3://%s/%s to %s", bucket, key, dest)
    s3.download_file(bucket, key, str(dest))
    return dest


def _bootstrap_model(sample_path: Path):
    """Train a tiny model from the sample events so the API is demo-able."""
    df = pd.read_json(sample_path)
    df["is_late"] = (df["delay_seconds"] > LATE_THRESHOLD).astype(int)
    df["hour"] = pd.to_datetime(df["timestamp"], unit="s").dt.hour
    df["dow"] = pd.to_datetime(df["timestamp"], unit="s").dt.dayofweek

    df_cat = pd.get_dummies(df[["route_id", "stop_id"]], drop_first=True)
    X = pd.concat([df[["delay_seconds", "hour", "dow"]], df_cat], axis=1)
    y = df["is_late"]

    from sklearn.ensemble import GradientBoostingClassifier

    model = GradientBoostingClassifier(random_state=42)
    model.fit(X, y)
    return model, list(X.columns)


def load_artifacts() -> None:
    global model, feature_names, model_source

    model_file: Optional[Path] = None
    features_file: Optional[Path] = None

    if MODEL_PATH and FEATURE_PATH and Path(MODEL_PATH).exists() and Path(FEATURE_PATH).exists():
        model_file = Path(MODEL_PATH)
        features_file = Path(FEATURE_PATH)
        model_source = "local-files"
    elif MODEL_BUCKET and MODEL_KEY:
        tmp_dir = Path("/tmp/transit-model")
        model_file = _download_from_s3(MODEL_BUCKET, MODEL_KEY, tmp_dir / "model.joblib")
        guessed_feature_key = FEATURE_KEY or MODEL_KEY.replace("model", "features").replace(".joblib", ".json")
        features_file = _download_from_s3(MODEL_BUCKET, guessed_feature_key, tmp_dir / "features.json")
        model_source = f"s3://{MODEL_BUCKET}/{MODEL_KEY}"
    else:
        logger.warning("No model artifacts provided; training bootstrap model from sample data")
        sample_path = Path(__file__).resolve().parents[2] / "data" / "sample_bus_events.json"
        model, feature_names = _bootstrap_model(sample_path)
        model_source = "bootstrap-sample"
        return

    if not model_file or not features_file:
        raise RuntimeError("Model and feature files are required")

    model = joblib.load(model_file)
    feature_names = _load_feature_names(features_file)
    logger.info("Loaded model from %s with %d features", model_source, len(feature_names))


@app.on_event("startup")
def startup_event() -> None:
    try:
        load_artifacts()
    except (ClientError, BotoCoreError, RuntimeError, FileNotFoundError) as exc:
        logger.error("failed to load model artifacts: %s", exc)


@app.get("/healthz")
def health() -> dict:
    status = "ok" if model is not None else "model_unloaded"
    return {"status": status, "model_source": model_source}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    if model is None or not feature_names:
        raise HTTPException(status_code=503, detail="Model not loaded")

    features = _feature_frame(payload, feature_names)
    prob = float(model.predict_proba(features)[0][1])
    is_late = prob >= 0.5 or payload.delay_seconds > LATE_THRESHOLD
    return PredictResponse(
        late_probability=prob,
        is_late=is_late,
        model_source=model_source,
        threshold_seconds=LATE_THRESHOLD,
    )
