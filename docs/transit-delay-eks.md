# Transit Delay Prediction on AWS + EKS

Use this as the main teaching track: predict bus arrival delays from open GTFS feeds, serve the model from EKS, and stream new events through Kinesis. Everything here is hands-on and maps to runnable manifests/code in `projects/transit-delay-eks/`.

## Real-world problem
- Passenger frustration and fleet inefficiency stem from late buses. We want a 0/1 or probabilistic delay flag for the next stop given recent telemetry and schedule metadata.
- Data is open: GTFS static files (`stops.txt`, `trips.txt`, `stop_times.txt`) plus GTFS-RT vehicle positions and trip updates published by many cities (e.g., NYC MTA, Transport for London, or any feed listed on https://transitfeeds.com/).

## High-level architecture
```
GTFS-RT feed → Kinesis (or MSK) → EKS consumer → S3 raw
                                    │
                                    ├─ EKS batch job (Argo) → S3 processed + features → Glue/Athena
                                    ├─ EKS train job (sklearn) → S3 models/
                                    └─ FastAPI on EKS → /predict (pulls latest model from S3)
                                                         │
                                                         └─ Prometheus scraping + Grafana dashboards
```

## Data contract
- **Vehicle position event (flattened):**
  ```json
  {
    "trip_id": "A12345",
    "route_id": "M15",
    "stop_id": "STOP_100",
    "timestamp": 1717000100,
    "latitude": 40.7302,
    "longitude": -73.9957,
    "delay_seconds": 220,
    "scheduled_arrival_ts": 1717000000
  }
  ```
- Label: `is_late = delay_seconds > 120` (tunable). Features: recent delays per route, headway variance, weather buckets, time-of-day, day-of-week, stop-level stats.

## Components to build
- **Ingestion consumer**: Python process in a Deployment, reads Kinesis/Kafka, validates schema, writes `raw/ingest_date=...` to S3.
- **Batch cleaner + feature builder**: Argo Workflow or CronJob runs a Spark/Ray-less Python job (pandas) to create training-friendly Parquet in `processed/`.
- **Training job**: Kubernetes Job that loads `processed/`, trains a baseline sklearn model (e.g., Gradient Boosting, XGBoost if available), writes `models/{timestamp}/model.joblib` and metrics JSON to S3.
- **Serving API**: FastAPI Deployment + Service (with HPA) that downloads the latest model at startup and exposes `/predict` and `/healthz`.
- **Observability**: Prometheus annotations on API + consumer, a simple alert on error rate, and a Grafana dashboard (importable JSON) for request latency and model score distribution.

## Learning path (suggested weeks)
1) **Week 1 – Foundations**: read GTFS docs, dry-run local consumer against saved sample events. Deploy EKS (small node group) and push a container image for the consumer.
2) **Week 2 – Data layer**: ship raw to S3, catalog with Glue, query in Athena. Add schema validation (pydantic) to the consumer.
3) **Week 3 – Features + training**: run the batch job, train the baseline model as a Kubernetes Job, log metrics to S3.
4) **Week 4 – Serving + autoscaling**: deploy FastAPI with HPA, add Prometheus scraping, and create a Grafana dashboard.
5) **Week 5 – Hardening**: add drift checks (PSI on delay distribution), retries/backoff on ingestion, IaC for missing pieces, and cost controls.

See `docs/transit-delay-walkthrough.md` for concrete commands and checkpoints.
