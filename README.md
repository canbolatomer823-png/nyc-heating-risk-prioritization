# AWS Data Analytics Pipeline Project

Primary teaching track: **Transit Delay Prediction on AWS + EKS**. You will ingest GTFS real-time bus data, build features, train a baseline model, and serve predictions from Kubernetes (EKS). The goal is to stay realistic: small, runnable components that map to real AWS services (Kinesis/S3/EKS/Glue/Athena) without hand-wavy placeholders.

Alternative capstone track: **NYC Heat Risk Prioritization System**. This track uses official NYC housing complaints, HPD building and violation data, NOAA weather data, and Census vulnerability data to forecast which buildings are most likely to generate heat-related complaint surges and should be prioritized for inspection. See `docs/nyc-heat-risk-charter.md`, `docs/nyc-heat-risk-class-presentation.md`, and `projects/nyc-heat-risk/`.

> 🎯 Learning outcome: confidently explain and demo how streaming ingest, batch feature building, model training, and API serving come together on AWS.

## Repository structure

```
aws-analytics-pipeline/
├── docs/                        # Architecture + walkthroughs
├── projects/transit-delay-eks/  # New EKS-based, end-to-end sample
│   ├── services/                # Ingest, training, FastAPI serving code
│   ├── k8s/                     # Deployments, Job, Service, HPA manifests
│   └── data/                    # Small GTFS-like sample events
├── terraform/                   # Existing S3 + Lambda bootstrap (can reuse)
├── lambda/                      # Sample ingest Lambda (legacy track)
├── glue/                        # PySpark job (legacy track)
└── notebooks/                   # Exploration template (legacy track)
```

- **EKS transit track:** see `docs/transit-delay-eks.md` (architecture) and `docs/transit-delay-walkthrough.md` (step-by-step). Code lives in `projects/transit-delay-eks/`.
- **Housing risk capstone:** see `docs/nyc-heat-risk-charter.md` (project charter), `docs/nyc-heat-risk-class-presentation.md` (30-minute class talk), and `projects/nyc-heat-risk/` (working folder).
- **Legacy data-lake track:** the original S3/Glue/SageMaker materials remain if you want a non-Kubernetes path.

## Start here (EKS transit track)
1. Read `docs/transit-delay-eks.md` to understand the problem, data contract, and architecture.
2. Follow `docs/transit-delay-walkthrough.md` for a guided MVP (local smoke test → deploy to EKS → hit `/predict`).
3. Swap the sample events with a real GTFS-RT feed from your city and iterate on features.

## What you will learn
- Designing a layered data flow: Kinesis/MSK → consumer → S3 raw/processed → Glue/Athena.
- Shipping Kubernetes workloads for ingest (Deployment), training (Job/Argo), and serving (FastAPI + HPA).
- Storing and loading model artifacts from S3, exposing `/predict`, and instrumenting with Prometheus.
- Communicating impact with clear docs, metrics JSON, and dashboards.

## Datasets (realistic options)
- GTFS static + real-time vehicle positions: many agencies publish public URLs (e.g., NYC MTA, Transport for London, others listed on transitfeeds.com).
- Weather enrichment: Open-Meteo or other free APIs if you want to explore feature interactions.

## Next actions
- Run the local smoke test from `projects/transit-delay-eks/services/ingest`.
- Build/push the three containers (ingest/api/train) and deploy the manifests under `projects/transit-delay-eks/k8s/`.
- Track your progress in `docs/learning-plan.md` and expand the observability and feature set as you go.
