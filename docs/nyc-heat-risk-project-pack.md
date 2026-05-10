# NYC Heating Complaint Risk Project Pack

Bu dosya, projede şu ana kadar üretilen ana parçaları tek yerde toplar.

## Ana dosyalar

- Proje klasörü: [projects/nyc-heat-risk](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk)
- README: [README.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/README.md)
- Charter: [nyc-heat-risk-charter.md](/Users/omer/aws-analytics-pipeline/docs/nyc-heat-risk-charter.md)
- Sınıf anlatımı: [nyc-heat-risk-class-presentation.md](/Users/omer/aws-analytics-pipeline/docs/nyc-heat-risk-class-presentation.md)
- Broşür: [nyc-heat-risk-brochure.md](/Users/omer/aws-analytics-pipeline/docs/nyc-heat-risk-brochure.md)
- Sunum: [nyc-heating-risk-final.pptx](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/outputs/nyc-heating-risk-final/output.pptx)
- Broşür çıktısı: [nyc-heating-brochure-final.pptx](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/outputs/nyc-heating-brochure-final/output.pptx)

## Kod

- ETL: [src/etl](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/src/etl)
- Modeling: [src/modeling](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/src/modeling)
- API: [src/api/app.py](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/src/api/app.py)
- AWS helpers: [src/aws](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/src/aws)

## Veri ve çıktılar

- Heat-season artifact root: [heat_season_2024_10_01_2025_05_31](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31)
- Main second-season OOT artifact root: [oot_heat_season_2025_10_01_2026_04_26](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/oot_heat_season_2025_10_01_2026_04_26)
- Sparse panel: [building_day_heat_panel.csv](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/processed/building_day_heat_panel.csv)
- Dense panel: [building_day_heat_panel_dense.csv](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/processed/building_day_heat_panel_dense.csv)
- Logistic scored: [logistic_regression_scored.csv](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/processed/logistic_regression_scored.csv)
- Priority output: [inspection_priority_latest_day.csv](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_latest_day.csv)

## Raporlar

- [heat_data_profile.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/heat_data_profile.md)
- [rolling_backtest_summary.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/rolling_backtest_summary.md)
- [logistic_regression_metrics.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/logistic_regression_metrics.md)
- [logistic_regression_ranking_metrics.csv](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/logistic_regression_ranking_metrics.csv)
- [statistical_model_metrics.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/statistical_model_metrics.md)
- [seasonal_anova.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/seasonal_anova.md)
- [inspection_priority_summary.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_summary.md)
- [inspection_policy_simulation.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_policy_simulation.md)
- [subgroup_fairness_calibration.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/subgroup_fairness_calibration.md)
- [error_analysis.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/error_analysis.md)
- [uncertainty_report.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/uncertainty_report.md)
- [train_test_drift_report.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/train_test_drift_report.md)
- [experiment_registry.csv](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/experiment_registry.csv)
- [r_statistical_replication.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/r_statistical_replication.md)
- [out_of_time_validation.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_validation.md)
- [out_of_time_ranking_metrics.csv](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_ranking_metrics.csv)

## Dürüst durum

Şu anki sistem:

- çalışan heat-season final build
- resmi veri tabanlı
- `baseline + calibrated logistic + GEE + Binomial GLMM diagnostic + Negative Binomial`
- `2024-10-01 -> 2025-05-31` penceresi
- `2025-10-01 -> 2026-04-25` ikinci heating-season out-of-time doğrulaması mevcut
- `CRE` entegre
- calibrated threshold + ranking metrics + seasonal ANOVA mevcut
- operasyonel simülasyon + subgroup fairness/calibration + hata analizi + uncertainty + drift + experiment registry mevcut
- R tarafında seasonal ANOVA ve daily weather Negative Binomial replikasyonu mevcut
- mixed-effects kontrolü `Binomial GLMM diagnostic` olarak eklendi; ana performans kanıtı değildir

Henüz tam değil:

- canlı AWS deploy doğrulaması
