# AGENTS.md — aws-analytics-pipeline

## Project overview

A teaching/learning repo for AWS data analytics pipelines. Two active projects, plus legacy scaffolding and side experiments.

| Project | Path | Purpose |
|---|---|---|
| NYC Heat Risk | `projects/nyc-heat-risk/` | Capstone: predict NYC building heat/hot water complaint risk, serve via FastAPI, deploy to EKS |
| Transit Delay EKS | `projects/transit-delay-eks/` | Teaching track: predict bus delays from GTFS-RT, serve from EKS |
| Legacy track | root `terraform/`, `lambda/`, `glue/`, `pipelines/` | Original S3/Glue/SageMaker bootstrap (reference only) |
| halisaha-proto | `frontend/halisaha-proto/` | React+Vite prototype (unrelated side project) |
| ecommerce-k8s | `projects/ecommerce-k8s/` | Side experiment (incomplete) |

## Python environment

- **Single workspace venv** at `.venv/` (Python 3.9). All projects share it.
- Activate: `source .venv/bin/activate` or use the full path `./.venv/bin/python`.
- `projects/nyc-heat-risk/requirements.txt` is the canonical dependency list for the main project.
- `projects/transit-delay-eks/services/*/requirements.txt` are per-service for the transit track.

## Commands

### NYC Heat Risk (most active project)

All commands are path-independent via `make -C`:

```bash
# Full training pipeline (builds modeling table if missing, trains, syncs experiment registry, builds lookup)
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk train

# Run all tests
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk test

# Start the FastAPI scoring API locally
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk serve

# Full analysis suite (policy-sim, fairness, error-analysis, uncertainty, drift, experiment-registry, r-analysis)
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk analysis-suite

# Out-of-time validation (requires OOT modeling table to exist)
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk oot-validation

# Local smoke test
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk smoke
```

### Transit Delay EKS

```bash
# Ingestion dry-run (local)
python services/ingest/consumer.py --events projects/transit-delay-eks/data/sample_bus_events.json --s3-bucket YOUR_BUCKET --dry-run

# Train locally
python services/train/train.py --input projects/transit-delay-eks/data/sample_bus_events.json --output-dir /tmp/models

# Run API locally
uvicorn services/api/main:app --reload --port 8000
```

## Architecture notes

### NYC Heat Risk data flow

1. **ETL** (`src/etl/`): Ingests NYC 311, HPD, NOAA GSOD, Census CRE data
2. **Modeling** (`src/modeling/`): Builds dense building-day panel → modeling table → trains logistic regression (+ GEE, GLMM, NB statistical models)
3. **Reporting** (`src/reporting/`): Priority lists, fairness reports, policy simulations, drift checks, experiment registry
4. **API** (`src/api/app.py`): FastAPI scoring API with endpoints `/health`, `/metadata`, `/priorities/latest`, `/dashboard`, `/records/{building_id}`, `/score`
5. **AWS** (`src/aws/`): Deployment helpers — env validation, asset rendering, ECR login, kubeconfig generation, bootstrap, preflight checks

### Key data windows (defined in `src/project_paths.py`)

- Final window: `heat_season_2024_10_01_2025_05_31`
- Out-of-time window: `oot_heat_season_2025_10_01_2026_04_26`
- All artifacts live under `data/windows/<window_name>/` with `raw/`, `processed/`, `models/`, `reports/` subdirs

### AWS deployment flow (NYC Heat Risk)

Env file: `projects/nyc-heat-risk/deploy/aws.env` (contains sentinel values like `AWS_ACCOUNT_ID=000000000000` — must be replaced before real deploy).

Order: `deploy-validate` → `deploy-render` → `k8s-check` → `aws-preflight-release` → `release`

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk release          # full publish/build/apply
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk release-dry-run   # preview commands only
```

- Credentials come from `~/.aws/credentials` and `~/.aws/config` (never stored in repo).
- Training/scoring runs locally before deploy; the Docker image only serves the API from S3 artifacts.

## Testing

- Framework: `unittest` (not pytest).
- Tests: `projects/nyc-heat-risk/tests/test_*.py` (8 test files covering API, reporting, priority, audit, supabase).
- Run: `make -C projects/nyc-heat-risk test`
- `backend/tests/` is empty; `backend/app/` is a stub.

## Conventions and gotchas

- **Do not run `pip install` at workspace root** — use per-project requirements files.
- **R scripts** require `/opt/homebrew/bin/Rscript` (macOS ARM). The `make r-analysis` target runs `src/modeling/r_heat_season_analysis.R`.
- **Dockerfile** uses `python:3.11-slim` (different from workspace venv's 3.9).
- **No CI/CD** configured — no GitHub workflows, no pre-commit hooks.
- **Git repo initialized** — single initial commit.
- `tmp/` and `logs/` directories are scratch space, safe to ignore.
- The `deploy/rendered/` directory is generated output from `deploy-render`.
