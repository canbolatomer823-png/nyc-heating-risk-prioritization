# ETL Scripts

## Current flow

For reproducible window builds, use the orchestration script:

```bash
python3 projects/nyc-heat-risk/src/etl/build_window_artifacts.py \
  --window-name heat_season_2024_10_01_2025_05_31 \
  --date-from 2024-10-01 \
  --date-to 2025-05-31 \
  --extract-limit 300000 \
  --reference-limit 5000 \
  --batch-size 300
```

This writes a self-contained window bundle under:

- `projects/nyc-heat-risk/data/windows/<window-name>/raw`
- `projects/nyc-heat-risk/data/windows/<window-name>/processed`
- `projects/nyc-heat-risk/data/windows/<window-name>/reports`

Legacy January prototype artifacts may still remain under the older root-level folders, but the active final workflow and all current deliverables should use the heat-season window bundle paths.

1. Download bounded official source extracts for the target heat-season window:

```bash
python3 projects/nyc-heat-risk/src/etl/download_official_data.py \
  --limit 300000 \
  --date-from 2024-10-01 \
  --date-to 2025-05-31
```

2. Download official NOAA GSOD weather summaries for the same date window:

```bash
python3 projects/nyc-heat-risk/src/etl/download_noaa_gsod_weather.py \
  --date-from 2024-10-01 \
  --date-to 2025-05-31
```

3. Download official tract-level Census CRE rows for NYC:

```bash
python3 projects/nyc-heat-risk/src/etl/download_nyc_cre_tracts.py
```

4. Download HPD building, registration, and violation rows linked to the extracted complaint buildings:

```bash
python3 projects/nyc-heat-risk/src/etl/download_linked_hpd_data.py --batch-size 300
```

5. Build the sparse `building-day` complaint panel:

```bash
python3 projects/nyc-heat-risk/src/etl/build_building_day_panel.py
```

6. Expand the sparse panel into a dense daily panel with lag, next-day target, weather, and CRE fields:

```bash
python3 projects/nyc-heat-risk/src/etl/build_dense_building_day_panel.py
```

7. Produce a lightweight data profile report:

```bash
python3 projects/nyc-heat-risk/src/etl/profile_heat_data.py
```

8. Audit sparse/dense join and feature quality:

```bash
python3 projects/nyc-heat-risk/src/etl/audit_panel_quality.py \
  --sparse-panel projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/processed/building_day_heat_panel.csv \
  --dense-panel projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/processed/building_day_heat_panel_dense.csv \
  --panel-end 2025-05-31 \
  --output projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/panel_quality_audit.md
```

9. Materialize the compact labeled modeling table used by the benchmark and inference scripts:

```bash
./.venv/bin/python projects/nyc-heat-risk/src/modeling/build_modeling_table.py
```

10. Score the dense panel with the first rule-based baseline:

```bash
python3 projects/nyc-heat-risk/src/modeling/baseline_risk_model.py
```

11. Run the expanding-window heat-season backtest:

```bash
./.venv/bin/python projects/nyc-heat-risk/src/modeling/rolling_backtest.py \
  --input projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/processed/building_day_heat_panel_dense.csv \
  --metrics-output projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/rolling_backtest_metrics.csv \
  --summary-output projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/rolling_backtest_summary.md \
  --chunksize 500000 \
  --min-train-months 2 \
  --max-train-rows 60000 \
  --negative-ratio 5 \
  --logistic-max-iter 1000
```

12. Train the first logistic regression benchmark:

```bash
./.venv/bin/python projects/nyc-heat-risk/src/modeling/logistic_regression_model.py
```

13. Train the inference-oriented statistical models:

```bash
./.venv/bin/python projects/nyc-heat-risk/src/modeling/statistical_models.py
```

14. Build the latest-day inspection priority report:

```bash
python3 projects/nyc-heat-risk/src/reporting/build_inspection_priority_report.py
```

## Output

The current final heat-season pipeline writes the following key artifacts:

- `projects/nyc-heat-risk/data/windows/<window-name>/processed/building_day_heat_panel.csv`
- `projects/nyc-heat-risk/data/windows/<window-name>/processed/building_day_heat_panel_dense.csv`
- `projects/nyc-heat-risk/data/windows/<window-name>/processed/building_day_modeling_table.csv`
- `projects/nyc-heat-risk/data/windows/<window-name>/processed/logistic_regression_scored.csv`
- `projects/nyc-heat-risk/data/windows/<window-name>/processed/record_lookup.sqlite`
- `projects/nyc-heat-risk/data/windows/<window-name>/processed/noaa_gsod_nyc_daily_summary.csv`
- `projects/nyc-heat-risk/data/windows/<window-name>/raw/census_cre_nyc_tract_2024.csv`
- `projects/nyc-heat-risk/data/windows/<window-name>/reports/heat_data_profile.md`
- `projects/nyc-heat-risk/data/windows/<window-name>/reports/panel_quality_audit.md`
- `projects/nyc-heat-risk/data/windows/<window-name>/reports/rolling_backtest_summary.md`
- `projects/nyc-heat-risk/data/windows/<window-name>/reports/rolling_backtest_metrics.csv`
- `projects/nyc-heat-risk/data/windows/<window-name>/reports/logistic_regression_metrics.md`
- `projects/nyc-heat-risk/data/windows/<window-name>/reports/statistical_model_metrics.md`
- `projects/nyc-heat-risk/data/windows/<window-name>/reports/statistical_model_coefficients.csv`
- `projects/nyc-heat-risk/data/windows/<window-name>/reports/inspection_priority_latest_day.csv`
- `projects/nyc-heat-risk/data/windows/<window-name>/reports/inspection_priority_summary.md`

This is the first end-to-end prototype phase. It proves:

- official-source extraction works,
- official NOAA daily weather enrichment works,
- official tract-level CRE enrichment works,
- linked HPD enrichment works at larger volume,
- the daily modeling table is reproducible,
- feature and join quality can be audited before modeling,
- equity coverage can be audited before modeling,
- expanding-window validation can be run on the full heat-season window,
- a rule-based and trainable benchmark can be compared,
- clustered logistic inference, diagnostic mixed-effects GLMM output, and count inference are available,
- the model can be turned into an equity-weighted inspection-priority output artifact.
