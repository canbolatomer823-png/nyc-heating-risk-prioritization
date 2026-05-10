CREATE SCHEMA IF NOT EXISTS nhr;

CREATE TABLE IF NOT EXISTS nhr.model_runs (
    model_run_id text PRIMARY KEY,
    project_name text NOT NULL DEFAULT 'nyc-heat-risk',
    window_label text NOT NULL,
    priority_date date NOT NULL,
    model_type text NOT NULL,
    calibration_method text,
    model_threshold double precision,
    scored_row_count bigint,
    priority_row_count integer NOT NULL,
    source_priority_csv text NOT NULL,
    source_metadata_json text,
    created_at_utc timestamptz,
    published_at timestamptz NOT NULL DEFAULT now(),
    notes text
);

CREATE TABLE IF NOT EXISTS nhr.daily_priority_buildings (
    model_run_id text NOT NULL REFERENCES nhr.model_runs(model_run_id) ON DELETE CASCADE,
    priority_date date NOT NULL,
    inspection_priority_rank integer NOT NULL,
    building_id text NOT NULL,
    building_bbl text,
    borough text,
    incident_address text,
    building_zip text,
    community_board text,
    census_tract text,
    raw_model_probability double precision,
    model_probability double precision NOT NULL,
    model_threshold double precision,
    model_prediction integer,
    equity_weighted_priority_score double precision,
    cre_vulnerability_index double precision,
    cre_high_vulnerability_flag integer,
    open_linked_violation_count integer,
    cumulative_complaints_prior integer,
    days_since_last_complaint_capped double precision,
    heat_sensor_program_flag integer,
    heat_sensor_active_flag integer,
    weather_heating_degree_c double precision,
    weather_freezing_any_flag integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (model_run_id, priority_date, inspection_priority_rank)
);

CREATE TABLE IF NOT EXISTS nhr.prediction_explanations (
    model_run_id text NOT NULL REFERENCES nhr.model_runs(model_run_id) ON DELETE CASCADE,
    priority_date date NOT NULL,
    inspection_priority_rank integer NOT NULL,
    building_id text NOT NULL,
    why_risky text NOT NULL,
    top_positive_contributors text,
    top_negative_contributors text,
    top_positive_contributors_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    top_negative_contributors_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (model_run_id, priority_date, inspection_priority_rank)
);

CREATE TABLE IF NOT EXISTS nhr.demo_proof_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_run_id text REFERENCES nhr.model_runs(model_run_id) ON DELETE CASCADE,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS daily_priority_buildings_date_rank_idx
    ON nhr.daily_priority_buildings (priority_date, inspection_priority_rank);

CREATE INDEX IF NOT EXISTS daily_priority_buildings_borough_idx
    ON nhr.daily_priority_buildings (borough);

CREATE INDEX IF NOT EXISTS prediction_explanations_building_idx
    ON nhr.prediction_explanations (building_id);

CREATE OR REPLACE VIEW nhr.latest_model_run AS
SELECT *
FROM nhr.model_runs
ORDER BY priority_date DESC, published_at DESC
LIMIT 1;

CREATE OR REPLACE VIEW nhr.latest_priority_with_explanations AS
SELECT
    p.model_run_id,
    p.priority_date,
    p.inspection_priority_rank,
    p.building_id,
    p.building_bbl,
    p.borough,
    p.incident_address,
    p.building_zip,
    p.community_board,
    p.census_tract,
    p.model_probability,
    p.equity_weighted_priority_score,
    p.cre_vulnerability_index,
    p.open_linked_violation_count,
    p.cumulative_complaints_prior,
    p.weather_heating_degree_c,
    e.why_risky,
    e.top_positive_contributors,
    e.top_negative_contributors
FROM nhr.daily_priority_buildings p
JOIN nhr.latest_model_run r
    ON r.model_run_id = p.model_run_id
LEFT JOIN nhr.prediction_explanations e
    ON e.model_run_id = p.model_run_id
    AND e.priority_date = p.priority_date
    AND e.inspection_priority_rank = p.inspection_priority_rank;

CREATE OR REPLACE VIEW nhr.latest_borough_priority_mix AS
SELECT
    borough,
    count(*) AS priority_building_count,
    round(avg(model_probability)::numeric, 4) AS avg_model_probability,
    round(avg(equity_weighted_priority_score)::numeric, 4) AS avg_equity_weighted_priority_score
FROM nhr.latest_priority_with_explanations
GROUP BY borough
ORDER BY priority_building_count DESC, borough;
