# Data Card - NYC Heating Risk

- Generated at: `2026-05-05 18:52:38 UTC`
- Unit of analysis: `building-day`.
- Prediction target: whether a building receives a next-day heat/hot water complaint.
- Final heat-season window: `2024-10-01 -> 2025-05-31`.
- Dense panel rows: `8,789,310`
- Latest priority date: `2025-05-30`

## Official Data Sources

- NYC 311 Service Requests from 2010 to Present.
- NYC HPD Housing Maintenance Code Complaints and Problems.
- NYC HPD Buildings Subject to HPD Jurisdiction.
- NYC HPD Multiple Dwelling Registrations.
- NYC HPD Housing Maintenance Code Violations.
- NYC HPD Heat Sensor Program building list.
- NOAA GSOD / GHCN weather data.
- Census Community Resilience Estimates tract-level extract.

## Feature Groups

- Complaint history: lag, rolling, cumulative, prior max, days since last complaint.
- Building/admin data: borough, management program, unit proxy, registration status.
- Violations: linked violation counts and open violation counts with as-of leakage controls.
- Weather: temperature, heating-degree load, freezing flags, precipitation, wind, cold shock.
- Equity context: tract-level CRE vulnerability and equity-weather interaction.

## Quality Controls

- No duplicate building-date rows in the dense panel.
- No missing weather rows in the dense panel.
- No future-dated violation features.
- No target, lag, rolling, cumulative, prior-max, or days-since mismatch rows.
- CRE coverage is high but not perfect; unmatched tract rows remain disclosed.

## Data Risks

- Complaint data reflects reporting behavior, not the full universe of heating failures.
- CRE tract vulnerability is contextual; it should not be interpreted as a building-level causal variable.
- Open-data refreshes can change future model behavior, so drift monitoring is required.
- The project should be presented as heating/hot-water risk, not summer heat-wave risk.

## Linked Evidence

- Panel quality audit: [panel_quality_audit.md](<project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/panel_quality_audit.md)
- Seasonal ANOVA: [seasonal_anova.md](<project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/seasonal_anova.md)
- Priority summary: [inspection_priority_summary.md](<project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_summary.md)
- Error analysis: [error_analysis.md](<project-root>/data/windows/heat_season_2024_10_01_2025_05_31/reports/error_analysis.md)
