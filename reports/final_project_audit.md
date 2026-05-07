# Final Project Audit

- Generated at: `2026-05-07 14:10:09 UTC`
- Overall status: `READY`
- Counts: `0 fail, 0 warn`

## Interpretation

- `OK`: ready or verified locally.
- `WARN`: intentional remaining live integration or non-blocking caveat.
- `FAIL`: must fix before presenting as complete.

## Model

- `OK` trained model bundle: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/models/logistic_regression_bundle.joblib (13,914 bytes)
- `OK` model metadata: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/models/logistic_regression_bundle.metadata.json (7,571 bytes)
- `OK` model bundle structure: contains model and metadata
- `OK` primary model type: logistic_regression
- `OK` decision threshold: 0.2
- `OK` held-out test metrics: F1=0.1641, precision=0.1946, recall=0.1419, AUC=0.8036
- `OK` Precision@50 metric: 0.2743

## Priority

- `OK` priority CSV: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_latest_day.csv (109,024 bytes)
- `OK` why_risky CSV: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_why_risky.csv (28,242 bytes)
- `OK` priority row count: 50 rows
- `OK` why_risky row count: 50 rows
- `OK` record lookup sqlite: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/processed/record_lookup.sqlite (1,292,828,672 bytes)

## Analysis

- `OK` seasonal ANOVA: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/seasonal_anova.md (1,883 bytes)
- `OK` policy simulation: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_policy_simulation.md (2,534 bytes)
- `OK` subgroup fairness/calibration: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/subgroup_fairness_calibration.md (1,309 bytes)
- `OK` error analysis: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/error_analysis.md (742 bytes)
- `OK` uncertainty report: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/uncertainty_report.md (1,209 bytes)
- `OK` drift report: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/train_test_drift_report.md (1,160 bytes)
- `OK` experiment registry: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/experiment_registry.csv (2,324 bytes)
- `OK` out-of-time validation: <project-root>/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_validation.md (3,320 bytes)
- `OK` out-of-time ranking metrics: <project-root>/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_ranking_metrics.csv (60,728 bytes)
- `OK` experiment registry rows: 6 rows
- `OK` OOT ranking rows: 828 rows

## Demo

- `OK` demo proof markdown: <project-root>/reports/demo_proof/demo_proof.md (2,880 bytes)
- `OK` demo health JSON: <project-root>/reports/demo_proof/health.json (1,239 bytes)
- `OK` demo score JSON: <project-root>/reports/demo_proof/score_response.json (2,745 bytes)
- `OK` demo dashboard HTML: <project-root>/reports/demo_proof/dashboard.html (6,623 bytes)
- `OK` demo dashboard status JSON: <project-root>/reports/demo_proof/dashboard_status.json (183 bytes)
- `OK` optional SQL reporting schema: <project-root>/sql/05_supabase_reporting_schema.sql (4,389 bytes)
- `OK` optional SQL demo query script: <project-root>/sql/06_supabase_demo_queries.sql (4,216 bytes)
- `OK` optional SQL reporting summary: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/supabase/supabase_reporting_summary.md (555 bytes)
- `OK` optional SQL reporting payload: <project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/supabase/supabase_reporting_payload.json (225,266 bytes)
- `OK` optional SQL query coverage: latest run, top priorities, borough mix, and demo events
- `OK` dashboard proof status: HTML endpoint rendered priority table
- `OK` optional SQL payload shape: 50 priority, 50 explanations, 6 demo events
- `OK` Supabase live publish: scoped out; hosted Supabase is not required for the final statistics project

## Portfolio

- `OK` model card: <project-root>/reports/model_card.md (2,787 bytes)
- `OK` data card: <project-root>/reports/data_card.md (2,643 bytes)
- `OK` demo evidence pack: <project-root>/reports/evidence_pack/README.md (3,131 bytes)
- `OK` dashboard visual summary: <project-root>/reports/evidence_pack/dashboard_summary.png (129,010 bytes)
- `OK` model card claim safety: diagnostic GLMM and primary metrics are explicit
- `OK` data card coverage: sources, feature groups, quality controls, and risks
- `OK` evidence pack run order: dashboard, visual summary, API proof, AWS proof, and audit

## Presentation

- `OK` final presentation PPTX: <project-root>/outputs/nyc-heating-risk-final/output.pptx (85,069 bytes)
- `OK` final presentation QR PPTX: <project-root>/outputs/nyc-heating-risk-final/output_with_qr.pptx (94,398 bytes)
- `OK` final presentation QR PDF: <project-root>/outputs/nyc-heating-risk-final/output_with_qr.pdf (1,476,864 bytes)
- `OK` brochure PPTX: <project-root>/outputs/nyc-heating-brochure-final/output.pptx (47,615 bytes)
- `OK` brochure PDF: <project-root>/outputs/nyc-heating-brochure-final/output.pdf (606,955 bytes)
- `OK` brochure QR PNG: <project-root>/outputs/nyc-heating-brochure-final/brochure_qr.png (13,140 bytes)
- `OK` brochure S3 URI: <project-root>/outputs/nyc-heating-brochure-final/brochure_s3_uri.txt (119 bytes)
- `OK` brochure QR presigned URL: <project-root>/outputs/nyc-heating-brochure-final/brochure_presigned_url.txt (418 bytes)
- `OK` brochure QR expiry: valid until 2026-05-13T15:08:11+00:00
- `OK` IST312 topic form DOCX: <project-root>/outputs/ist312-final-sunumu/omer_canbolat_ist312_final_sunumu.docx (39,578 bytes)

## Aws

- `OK` AWS env file: <project-root>/deploy/aws.env (286 bytes)
- `OK` AWS account id: REDACTED_AWS_ACCOUNT_ID
- `OK` IRSA role ARN: arn:aws:iam::REDACTED_AWS_ACCOUNT_ID:role/nyc-heat-risk-irsa
- `OK` AWS credentials: /Users/omer/.aws/credentials
- `OK` AWS config: /Users/omer/.aws/config
- `OK` docker CLI: /usr/local/bin/docker
- `OK` docker daemon: 29.4.0
- `OK` kubectl: /usr/local/bin/kubectl
- `OK` AWS live deploy proof: captured timestamped live proof: <project-root>/reports/aws_live_deploy_proof.md
- `OK` AWS shutdown proof: short-lived EKS resources absent after demo: <project-root>/reports/aws_shutdown_proof.md

## Claims

- `OK` risky wording scan: no unsafe positive claims found in main docs

## Short Answer

- Core analytics, local API proof, presentation, brochure, QR access, and AWS proof are audit-ready if there are no `FAIL` rows above.
- Hosted Supabase is intentionally scoped out; optional local SQL payloads remain as an appendix only.
- AWS is complete as a timestamped cloud proof only when live endpoint proof and shutdown proof both pass.
