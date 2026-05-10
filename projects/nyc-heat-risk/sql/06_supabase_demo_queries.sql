-- NYC Heating Risk - Supabase live demo queries
-- Run after:
--   1) sql/05_supabase_reporting_schema.sql
--   2) make supabase-publish
--
-- These queries are read-only and are designed for Supabase SQL Editor.

-- 1) Latest published model run.
SELECT
    model_run_id,
    window_label,
    priority_date,
    model_type,
    calibration_method,
    round(model_threshold::numeric, 4) AS model_threshold,
    scored_row_count,
    priority_row_count,
    published_at
FROM nhr.latest_model_run;

-- 2) Row counts proving that the reporting layer was populated.
SELECT 'nhr.model_runs' AS object_name, count(*)::bigint AS row_count
FROM nhr.model_runs
UNION ALL
SELECT 'nhr.daily_priority_buildings', count(*)::bigint
FROM nhr.daily_priority_buildings
UNION ALL
SELECT 'nhr.prediction_explanations', count(*)::bigint
FROM nhr.prediction_explanations
UNION ALL
SELECT 'nhr.demo_proof_events', count(*)::bigint
FROM nhr.demo_proof_events
ORDER BY object_name;

-- 3) Top 10 inspection-priority buildings with row-level "why risky" explanation.
SELECT
    inspection_priority_rank,
    building_id,
    borough,
    incident_address,
    building_zip,
    round(model_probability::numeric, 4) AS probability,
    round(equity_weighted_priority_score::numeric, 4) AS equity_score,
    round(cre_vulnerability_index::numeric, 4) AS cre_vulnerability,
    open_linked_violation_count,
    cumulative_complaints_prior,
    why_risky
FROM nhr.latest_priority_with_explanations
ORDER BY inspection_priority_rank
LIMIT 10;

-- 4) Borough-level operational mix.
SELECT
    borough,
    priority_building_count,
    avg_model_probability,
    avg_equity_weighted_priority_score
FROM nhr.latest_borough_priority_mix;

-- 5) Top-priority group versus the rest of the published priority list.
WITH ranked AS (
    SELECT
        CASE
            WHEN inspection_priority_rank <= 10 THEN 'top_10'
            WHEN inspection_priority_rank <= 25 THEN 'rank_11_25'
            ELSE 'rank_26_50'
        END AS rank_band,
        model_probability,
        equity_weighted_priority_score,
        cre_vulnerability_index,
        open_linked_violation_count,
        cumulative_complaints_prior,
        weather_heating_degree_c
    FROM nhr.latest_priority_with_explanations
)
SELECT
    rank_band,
    count(*) AS buildings,
    round(avg(model_probability)::numeric, 4) AS avg_probability,
    round(avg(equity_weighted_priority_score)::numeric, 4) AS avg_equity_score,
    round(avg(cre_vulnerability_index)::numeric, 4) AS avg_cre_vulnerability,
    round(avg(open_linked_violation_count)::numeric, 2) AS avg_open_violations,
    round(avg(cumulative_complaints_prior)::numeric, 2) AS avg_prior_complaints,
    round(avg(weather_heating_degree_c)::numeric, 2) AS avg_heating_degree_c
FROM ranked
GROUP BY rank_band
ORDER BY
    CASE rank_band
        WHEN 'top_10' THEN 1
        WHEN 'rank_11_25' THEN 2
        ELSE 3
    END;

-- 6) Explanation completeness check.
SELECT
    count(*) AS priority_rows,
    count(why_risky) AS rows_with_explanation,
    count(*) - count(why_risky) AS rows_missing_explanation
FROM nhr.latest_priority_with_explanations;

-- 7) Drill into the single highest-risk building.
SELECT
    p.inspection_priority_rank,
    p.building_id,
    p.borough,
    p.incident_address,
    p.model_probability,
    p.equity_weighted_priority_score,
    p.cre_vulnerability_index,
    p.open_linked_violation_count,
    p.cumulative_complaints_prior,
    p.weather_heating_degree_c,
    e.top_positive_contributors_json,
    e.top_negative_contributors_json,
    e.why_risky
FROM nhr.daily_priority_buildings p
JOIN nhr.latest_model_run r
    ON r.model_run_id = p.model_run_id
LEFT JOIN nhr.prediction_explanations e
    ON e.model_run_id = p.model_run_id
    AND e.priority_date = p.priority_date
    AND e.inspection_priority_rank = p.inspection_priority_rank
WHERE p.inspection_priority_rank = 1;

-- 8) Local API demo proof events mirrored into Postgres.
SELECT
    event_type,
    created_at,
    payload ->> 'status' AS status,
    payload ->> 'model_type' AS model_type,
    payload ->> 'priority_row_count' AS priority_row_count
FROM nhr.demo_proof_events
ORDER BY created_at DESC, event_id DESC;

