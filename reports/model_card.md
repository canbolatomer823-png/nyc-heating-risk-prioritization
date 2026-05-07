# Model Card - NYC Heating Risk

- Generated at: `2026-05-05 18:52:33 UTC`
- Model role: operational ranking for next-day heating/hot water complaint risk.
- Primary use: prioritize which buildings should be reviewed first when inspection capacity is limited.
- Non-use: do not use as an automatic enforcement or tenant eligibility decision system.

## Model

- Type: `logistic_regression`
- Calibration: `platt`
- Decision threshold: `0.2`
- Primary evidence: calibrated logistic ranking, not GLMM.
- Statistical support: GEE, Negative Binomial, ANOVA, R replication, fairness/calibration, uncertainty, drift.

## Data Split

- `train`: `2024-10-01` -> `2025-02-22`
- `calibration`: `2025-02-23` -> `2025-03-18`
- `threshold_tuning`: `2025-03-19` -> `2025-04-11`
- `test`: `2025-04-12` -> `2025-05-30`

## Held-Out Test Metrics

- Rows: `1772330`
- Precision: `0.1946`
- Recall: `0.1419`
- F1: `0.1641`
- ROC AUC: `0.8036`
- Average precision: `0.1004`
- Brier score: `0.0060`
- Mean Precision@50: `0.2743`
- Mean Lift@50: `47.3438`

## Out-of-Time Evidence

- Report: [out_of_time_validation.md](<project-root>/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_validation.md)
- Precision: 0.4571
- Recall: 0.1381
- F1: 0.2121
- ROC AUC: 0.8107
- Mean Precision@50: 0.6893

## Known Limitations

- This is a decision-support prototype, not an automatic inspection system.
- AWS live deploy should be presented as timestamped proof unless the short-lived endpoint is recreated for demo day.
- GLMM is diagnostic only because optimizer convergence is not strong enough for primary claims.
- The model ranks operational risk; it does not prove causality.
- Equity weighting is transparent and auditable, but it still needs policy review before real use.

## Linked Evidence

- Metrics: [logistic_regression_metrics.md](<project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/logistic_regression_metrics.md)
- Policy simulation: [inspection_policy_simulation.md](<project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_policy_simulation.md)
- Fairness/calibration: [subgroup_fairness_calibration.md](<project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/subgroup_fairness_calibration.md)
- Uncertainty: [uncertainty_report.md](<project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/uncertainty_report.md)
- Drift: [train_test_drift_report.md](<project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/train_test_drift_report.md)
