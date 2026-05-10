# NYC Heating and Hot Water Complaint Risk Prioritization

This folder contains a real-data prototype for predicting which NYC residential buildings are most likely to generate next-day `heat/hot water` complaints and turning that into an inspection-priority list.

## Problem framing

This project is **not** a summer heat-wave model.

It models building-level `heat/hot water` complaint risk, which is most naturally tied to:

- NYC `Heat Season` obligations for heating service
- year-round hot water service obligations
- cold-weather shocks and chronic building failure patterns

Current final heat-season window:

- `2024-10-01 -> 2025-05-31`
- Artifacts: [data/windows/heat_season_2024_10_01_2025_05_31](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31)
- This wider heat-season window now has quality audit, backtest, benchmark retraining, and equity-weighted priority artifacts.

Archived January-only prototype:

- `2025-01-01 -> 2025-01-31`
- Legacy root-level `reports/` files refer to this earlier staging window and are kept only for traceability.

## What is actually implemented

- Official NYC and NOAA data ingestion
- Building-linked complaint panel
- Dense `building-day` panel
- Compact labeled modeling table for benchmark/inference training
- NOAA GSOD daily weather enrichment
- Official tract-level Census CRE vulnerability enrichment
- Temporal complaint-history features
- As-of-date violation features with temporal leakage fix
- Dense-panel as-of/carry-forward features with leakage checks
- Automated sparse/dense panel quality audit
- Expanding-window monthly backtest on the full heat-season staging panel
- Rule-based baseline model
- Logistic regression benchmark
- `GEE logistic` clustered inference model
- `Binomial GLMM` mixed-effects diagnostic model
- `Negative Binomial` next-day count model
- Inspection priority list
- Equity-weighted inspection priority ranking
- Row-level `why_risky` feature explanations for the priority list
- Daily inspection-capacity policy simulation
- Subgroup fairness / calibration report on held-out predictions
- Segment-level held-out error analysis
- Bootstrap uncertainty / confidence-interval reporting
- Train-vs-test drift reporting
- Forward out-of-time validation on a non-overlapping future window
- Experiment registry synced from benchmark and inference artifacts
- R-side statistical replication for ANOVA and daily weather count regression
- Indexed SQLite record lookup artifact for fast `/records` API queries
- FastAPI scoring API
- Docker packaging
- AWS/S3/ECR/EKS deployment flow with timestamped live endpoint proof
- AWS shutdown proof for the short-lived EKS demo resources

Deployment note:

- The AWS runtime image is intentionally lean and serves the API from `S3` artifacts.
- Training, scoring, and artifact publishing happen before `kubectl apply`; they are not run as a Kubernetes job in the final release flow.

## What is not implemented yet

- Hosted Supabase live publish is intentionally scoped out; optional SQL payload files remain only as an appendix.
- The AWS endpoint is intentionally short-lived for cost control; use the saved live proof and shutdown proof instead of claiming the deleted URL is still online.

## Official datasets

- 311 Service Requests from 2010 to Present: `erm2-nwe9`
- Housing Maintenance Code Complaints and Problems: `ygpa-z7cr`
- Buildings Subject to HPD Jurisdiction: `kj4p-ruqc`
- Multiple Dwelling Registrations: `tesw-yqqr`
- Housing Maintenance Code Violations: `wvxf-dwi5`
- Buildings Selected for the Heat Sensor Program: `h4mf-f24e`
- Census Community Resilience Estimates (CRE), tract-level 2024 API extract
- NOAA Global Surface Summary of the Day (GSOD) and NOAA GHCN-Daily

## Current final metrics

Expanded heat-season final profile:

- `282,296` complaint records
- `36,170` unique buildings
- `8,789,310` dense `building-day` rows
- `8,719,812` dense rows with tract-level CRE coverage (`99.21%`)
- `68,283` dense rows still have nonempty tract values without a CRE match
- Quality audit: [panel_quality_audit.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/panel_quality_audit.md)
- Rolling backtest: [rolling_backtest_summary.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/rolling_backtest_summary.md)
- Heat-season benchmark metrics: [logistic_regression_metrics.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/logistic_regression_metrics.md)
- Heat-season benchmark ranking metrics: [logistic_regression_ranking_metrics.csv](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/logistic_regression_ranking_metrics.csv)
- Heat-season statistical metrics: [statistical_model_metrics.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/statistical_model_metrics.md)
- Heat-season seasonal ANOVA: [seasonal_anova.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/seasonal_anova.md)
- Heat-season priority summary: [inspection_priority_summary.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_summary.md)
- Heat-season why-risky explanations: [inspection_priority_why_risky.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_why_risky.md)
- Policy simulation: [inspection_policy_simulation.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_policy_simulation.md)
- Subgroup fairness / calibration: [subgroup_fairness_calibration.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/subgroup_fairness_calibration.md)
- Error analysis: [error_analysis.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/error_analysis.md)
- Uncertainty report: [uncertainty_report.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/uncertainty_report.md)
- Drift report: [train_test_drift_report.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/train_test_drift_report.md)
- Experiment registry: [experiment_registry.csv](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/experiment_registry.csv)
- R replication report: [r_statistical_replication.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/r_statistical_replication.md)
- Main second-season out-of-time window: [oot_heat_season_2025_10_01_2026_04_26](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/oot_heat_season_2025_10_01_2026_04_26)
- Main second-season out-of-time report: [out_of_time_validation.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_validation.md)

Expanded heat-season rolling backtest, test-month mean:

- Baseline F1: `0.2699`
- Baseline ROC AUC: `0.7834`
- SGD logistic F1: `0.2000`
- SGD logistic ROC AUC: `0.7992`

Interpretation:

- The rule-based baseline is stronger on thresholded F1.
- The trainable logistic model ranks risk better by ROC AUC, and the latest version now includes explicit calibration and threshold tuning.

Expanded heat-season retrained logistic benchmark:

- Calibration method: `platt`
- Threshold tuning beta: `0.5`
- Threshold split threshold: `0.2`
- Test F1: `0.1641`
- Test ROC AUC: `0.8036`
- Test average precision: `0.1004`
- Test predicted positive rate: `0.0043`
- Test actual positive rate: `0.0059`
- Test Brier score: `0.0060`
- Mean Precision@10: `0.4531`
- Mean Precision@25: `0.3494`
- Mean Precision@50: `0.2743`
- Mean Lift@50: `47.3438`

Interpretation:

- On the full heat-season window, calibration pulls mean probabilities much closer to actual late-season prevalence.
- The calibrated benchmark still behaves more like a ranking model than a decision-threshold model, but it no longer produces obviously inflated probability levels.
- The operational ranking is much stronger than the raw thresholded F1 suggests: on the held-out period, the top 50 buildings per day contain positives about `27.4%` of the time versus a base rate of only `0.59%`.
- CRE features are now present in the trained artifact and in the equity-weighted priority ranking, but they are not yet dominant drivers in the benchmark coefficients.

Expanded heat-season sampled statistical inference:

- GEE validation threshold: `0.25`
- GEE test F1: `0.2247`
- GLMM diagnostic validation threshold: `0.85`
- GLMM diagnostic test F1: `0.1277`
- GLMM optimizer converged: `false`
- GLMM random-intercept SD: `0.3797`
- CRE vulnerability in GEE: `coef=0.9484`, `OR=2.5815`, `p=0.3746`
- Equity-weather interaction in GEE: `coef=-0.2565`, `OR=0.7737`, `p=0.5892`
- NB test MAE: `0.0699`

Interpretation:

- The clustered GEE model is now numerically stable on the expanded window and gives interpretable equity-aware inference on a stratified sample.
- The project includes a building-panel GLMM diagnostic, but the VB optimizer does not fully converge, so it is not used as primary performance evidence.
- CRE vulnerability remains positive in the GEE risk model, while the interaction term is not treated as a primary claim in the refreshed statistical sample.
- The Negative Binomial count model remains weaker on the CRE terms than the GEE classification model.

Heat-season seasonal ANOVA:

- Daily complaint load monthly ANOVA: `F=33.6227`, `p<0.0001`, `eta_sq=0.5004`
- Daily positive-building monthly ANOVA: `F=33.9890`, `p<0.0001`, `eta_sq=0.5031`
- Seasonal-phase complaint ANOVA: `F=80.5074`, `p<0.0001`, `eta_sq=0.4015`
- Seasonal-phase positive-building ANOVA: `F=79.1735`, `p<0.0001`, `eta_sq=0.3975`

Interpretation:

- The complaint burden is not flat across the heat season; month and season-phase effects are both large enough to defend statistically in class.
- January 2025 is the highest-load month in the current window, while May 2025 is the lowest-load month.

Held-out subgroup fairness / calibration:

- Overall ECE: `0.005146`
- Lowest borough recall: `BROOKLYN = 0.095612`
- Highest borough recall: `BRONX = 0.184242`
- Borough recall spread: `0.088630`
- Worst management-program ECE: `7A = 0.008514`
- High-vulnerability CRE bucket recall: `0.147102`
- Low-vulnerability CRE bucket recall: `0.115702`

Interpretation:

- The benchmark is not uniformly calibrated or equally sensitive across operational subgroups.
- High-vulnerability tracts receive higher recall but also carry worse calibration error, which is exactly the type of tradeoff a modern audit should surface before deployment.

Second heating-season out-of-time validation on `2025-10-01 -> 2026-04-25`:

- Rows: `8,344,170`
- Actual positive rate: `0.0263`
- Precision: `0.4571`
- Recall: `0.1381`
- F1: `0.2121`
- Average precision: `0.2228`
- ROC AUC: `0.8107`
- Mean Precision@10: `0.8159`
- Mean Precision@50: `0.6893`

Interpretation:

- The frozen heat-season model remains strong when moved into the next real heating season without retraining.
- Ranking quality is substantially stronger than the earlier summer forward window because the operational regime matches the original problem more closely.
- This is a much more defensible deployment-style result: the model is not only useful in-window, but remains useful when time moves forward into the next heating season.

R replication layer:

- R-side ANOVA reproduces the same monthly complaint result: `F=33.6227`, `p=3.29e-32`, `eta_sq=0.5004`
- R-side ANOVA reproduces the same monthly positive-building result: `F=33.9890`, `p=1.76e-32`, `eta_sq=0.5031`
- R-side daily weather Negative Binomial gives a heating-degree effect of `2.1188x` with `p=7.17e-146`

Interpretation:

- The project now has a visible R component that reproduces core seasonal inference rather than relying only on Python outputs.
- This R layer is intentionally aggregate-level and complements, rather than replaces, the building-day benchmark and Python inference stack.

The current heat-season build should be read from the expanded-window sections above. Legacy January-only outputs remain archived on disk but are not the primary result.

## Main outputs

- [heat_season heat_data_profile.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/heat_data_profile.md)
- [heat_season inspection_priority_summary.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_summary.md)
- [nyc-heating-risk-final.pptx](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/outputs/nyc-heating-risk-final/output.pptx)
- [nyc-heating-brochure-final.pptx](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/outputs/nyc-heating-brochure-final/output.pptx)
- [heat_season logistic metrics](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/logistic_regression_metrics.md)
- [heat_season logistic ranking metrics](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/logistic_regression_ranking_metrics.csv)
- [heat_season inspection priority summary](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_summary.md)
- [heat_season model metadata](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/models/logistic_regression_bundle.metadata.json)
- [heat_season record lookup db](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/processed/record_lookup.sqlite)
- [heat_season statistical coefficients](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/statistical_model_coefficients.csv)
- [live demo proof guide](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/DEMO_PROOF_GUIDE.md)
- [final rehearsal pack](/Users/omer/aws-analytics-pipeline/docs/nyc-heat-risk-final-rehearsal-pack.md)
- [heat_season seasonal ANOVA](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/seasonal_anova.md)
- [heat_season policy simulation](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_policy_simulation.md)
- [heat_season subgroup fairness and calibration](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/subgroup_fairness_calibration.md)
- [heat_season error analysis](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/error_analysis.md)
- [heat_season uncertainty report](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/uncertainty_report.md)
- [heat_season drift report](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/train_test_drift_report.md)
- [heat_season experiment registry](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/experiment_registry.csv)
- [heat_season R statistical replication](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/r_statistical_replication.md)
- [second-season out-of-time validation report](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_validation.md)
- [second-season out-of-time ranking metrics](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_ranking_metrics.csv)
- [model card](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/model_card.md)
- [data card](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/data_card.md)
- [demo evidence pack](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/evidence_pack/README.md)
- [dashboard visual summary](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/evidence_pack/dashboard_summary.png)
- [Optional SQL reporting guide](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/SUPABASE_REPORTING_GUIDE.md)
- [Optional SQL demo queries](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/sql/06_supabase_demo_queries.sql)

## API

The project includes a lightweight scoring API:

- [app.py](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/src/api/app.py)

Endpoints:

- `GET /health`
- `GET /metadata`
- `GET /priorities/latest?top_n=20`
- `GET /dashboard?top_n=20`
- `GET /records/{building_id}?calendar_date=YYYY-MM-DD`
- `POST /score`

## Run locally

From the repo root:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk modeling-table
./.venv/bin/python projects/nyc-heat-risk/src/modeling/logistic_regression_model.py
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk analysis-suite
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk r-analysis
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk oot-validation
./.venv/bin/python projects/nyc-heat-risk/src/modeling/statistical_models.py
./.venv/bin/python projects/nyc-heat-risk/src/reporting/build_inspection_priority_report.py
./.venv/bin/uvicorn api.app:app --app-dir projects/nyc-heat-risk/src --host 0.0.0.0 --port 8000
```

Path-independent helpers:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk train
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk smoke
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk portfolio-pack
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk final-audit
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk deploy-render
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk k8s-check
```

`demo-proof` generates the local API proof. Optional SQL payload files may also be produced for appendix use, but hosted Supabase is not part of the required final scope.
`portfolio-pack` writes the model card, data card, and demo evidence pack used for presentation proof.
`final-audit` writes [final_project_audit.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/final_project_audit.md) and separates real failures from known live-deploy blockers.

After AWS release, capture live endpoint proof with:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk aws-live-proof BASE_URL=http://YOUR_AWS_LOAD_BALANCER
```

After deleting the short-lived EKS resources, capture shutdown proof with:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk aws-shutdown-proof
```

Saved AWS evidence:

- [AWS live deploy proof](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/aws_live_deploy_proof.md)
- [AWS shutdown proof](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/aws_shutdown_proof.md)

## Deployment

AWS deployment scaffolding is documented here:

- [nyc-heat-risk-eks.md](/Users/omer/aws-analytics-pipeline/docs/nyc-heat-risk-eks.md)
- [deploy/README.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/README.md)

## Honest next steps

1. Keep the calibrated full-window logistic model as the primary operational ranking result, with GEE/NB as inference support and GLMM as a diagnostic-only mixed-effects check.
2. Recreate the EKS live endpoint only on demo day if a currently reachable URL is required; otherwise present the timestamped AWS proof and shutdown proof.
