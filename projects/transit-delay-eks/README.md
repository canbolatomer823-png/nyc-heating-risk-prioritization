# Transit Delay Prediction on AWS + EKS

This folder contains the runnable pieces for the teaching track described in `docs/transit-delay-eks.md`. Everything is small on purpose so you can iterate quickly: one consumer, one training job, one FastAPI service, and a handful of Kubernetes manifests.

## Components
- `services/ingest/consumer.py`: Reads GTFS-like events (Kinesis/Kafka or local JSON), validates, and writes to S3 under `raw/`.
- `services/train/train.py`: Batch job (Kubernetes Job/Argo step) that builds simple features, trains a baseline classifier, and saves artifacts + metrics to S3.
- `services/api/main.py`: FastAPI app that loads the latest model from S3 at startup and exposes `/predict` + `/healthz`.
- `k8s/`: Namespace, Deployments, Service, HPA, and Job manifests with Prometheus scrape annotations.
- `data/sample_bus_events.json`: Three small events to test without a live feed.

## Local development
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r services/ingest/requirements.txt
pip install -r services/train/requirements.txt
pip install -r services/api/requirements.txt
```

### Ingestion dry-run
```bash
python services/ingest/consumer.py --events projects/transit-delay-eks/data/sample_bus_events.json --s3-bucket YOUR_BUCKET --dry-run
```

### Train locally (uses the processed parquet if present; falls back to sample)
```bash
python services/train/train.py --input projects/transit-delay-eks/data/sample_bus_events.json --output-dir /tmp/models
```

### Run the API locally
```bash
uvicorn services/api/main:app --reload --port 8000
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"route_id":"M15","stop_id":"STOP_100","delay_seconds":180,"timestamp":1717000100}'
```

## Deploying to EKS (short version)
1. Build/push images for `ingest`, `api`, and `train` (see `docs/transit-delay-walkthrough.md`).
2. Update image names + S3/Kinesis env vars in the manifests under `k8s/`.
3. `kubectl apply -f k8s/` and verify pods are READY in the `transit-delay` namespace.

## Configuration
- Common env vars: `MODEL_BUCKET`, `RAW_BUCKET`, `PROCESSED_BUCKET`, `KINESIS_STREAM`, `AWS_REGION`.
- Defaults in code point to local testing; override for your account.
- Prometheus scraping is enabled via annotations on the Deployments.
