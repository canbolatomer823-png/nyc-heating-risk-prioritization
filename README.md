# NYC Heating Complaint Risk Prioritization

Portfolio-ready data science project by **Omer Canbolat**.

This project uses official NYC 311, HPD, NOAA and Census CRE data to predict which residential buildings have higher next-day heating / hot-water complaint risk, then converts the prediction into an interpretable inspection priority list.

## Project Goal

City inspection capacity is limited. Inspectors cannot visit every building at the same time, so the practical decision question is:

**Which buildings should be checked first tomorrow?**

This repository is a decision-support prototype. It does **not** claim to eliminate complaints or automate enforcement decisions.

## What Is Included

- Python source code for ETL, modeling, reporting, API serving and AWS helper workflows.
- Statistical modeling layer: calibrated logistic ranking, ANOVA, Negative Binomial, GEE and GLMM-style diagnostics.
- FastAPI scoring API and Docker packaging.
- SQL appendix for analytics / reporting schemas.
- Kubernetes manifests and safe AWS deployment helper examples.
- Portfolio assets: project presentation, brochure, one-page summary and start guide.
- Evidence reports: model card, data card, final audit and demo proof.

## What Is Excluded

For safety and size reasons, this public repository intentionally excludes:

- raw data files
- generated dense panels
- trained model binaries
- local SQLite lookup artifacts
- `.env` files
- AWS credentials
- Supabase credentials
- generated kubeconfig files
- full local output folders

## Key Results

- Complaint records: `282,296`
- Unique buildings: `36,170`
- Dense building-day rows: `8.79M`
- Mean Precision@50: `0.274`
- Lift@50: `47.3x`
- Out-of-time Mean Precision@50: `0.689`
- Final audit: `READY`, `0 fail`, `0 warn`

## Main Methods

- **Logistic regression:** primary model for next-day 0/1 complaint risk and operational ranking.
- **ANOVA:** tests whether average complaint levels differ by month / season.
- **Negative Binomial:** supports count-style complaint volume interpretation.
- **GEE / GLMM diagnostics:** checks repeated-building panel structure; not the primary decision model.
- **Calibration / backtesting / out-of-time validation:** checks whether scores remain useful beyond one split.

## Repository Map

```text
src/                 Python ETL, modeling, reporting, API and AWS helper code
tests/               Unit tests for API, reporting, audit and deployment proof helpers
sql/                 Analytics and reporting SQL appendix
k8s/                 Kubernetes manifests
deploy/              Safe deployment docs, examples and helper scripts
reports/             Portfolio-safe evidence reports
portfolio_assets/    Presentation, brochure and one-page summary PDFs
```

## How To Review

Start here:

1. Open `portfolio_assets/NYC_Heating_Risk_Baslangic_Rehberi_Omer_Canbolat.pdf`.
2. Open `portfolio_assets/NYC_Heating_Risk_Final_Sunum_Public_Omer_Canbolat.pdf`.
3. Open `portfolio_assets/NYC_Heating_Risk_Brosur_Omer_Canbolat.pdf`.
4. For technical proof, review `reports/final_project_audit.md`, `reports/model_card.md` and `reports/data_card.md`.

## Local Development Notes

The original full local project uses generated artifacts under `data/windows/...`, which are not committed here because they are large. To fully retrain or reproduce the final data window, the ETL scripts must be run against the official public data sources and the generated artifacts must be rebuilt locally.

Typical local commands in the full workspace:

```bash
make train
make test
make final-audit
make class-demo-check
make serve
```

## CV Summary

Built a reproducible data science prototype using NYC 311, HPD, NOAA and Census CRE data to predict next-day heating/hot-water complaint risk at building-day level. Developed calibrated logistic ranking, ANOVA, Negative Binomial diagnostics, validation/backtesting reports, FastAPI scoring API, Dockerized demo and AWS deployment proof workflow.
