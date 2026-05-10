# Supabase Live Checklist

This checklist is for the final class/demo day when the local model outputs should be visible in a real Supabase Postgres database.

## Goal

Prove that the project output is not only a local CSV. The final priority list, row-level explanations, model-run metadata, and demo proof events should be queryable from hosted Postgres.

Supabase is used here only as the SQL reporting layer. It does not train the model and does not replace AWS live deploy.

## Before You Start

- Create a Supabase project.
- Open `Project Settings > Database > Connection string`.
- Use the `Session pooler` connection string.
- Keep the database password local. Do not paste it into chat and do not commit it.

Example local-only environment variable:

```bash
export SUPABASE_DB_URL='postgresql://postgres.PROJECT_REF:YOUR_DATABASE_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require'
```

Alternative local-only file:

```bash
cp /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/supabase.env.example \
  /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/supabase.env
```

Then edit `deploy/supabase.env`. The project Makefile loads it automatically, and Git ignores it.

## Step 1 - Build Local Proof Artifacts

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof
```

Expected local outputs:

- [demo_proof.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/demo_proof.md)
- [supabase_reporting_payload.json](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/supabase/supabase_reporting_payload.json)
- [supabase_reporting_summary.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/supabase/supabase_reporting_summary.md)

## Step 2 - Create Supabase Schema

Open Supabase SQL Editor and run:

- [05_supabase_reporting_schema.sql](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/sql/05_supabase_reporting_schema.sql)

This creates:

- `nhr.model_runs`
- `nhr.daily_priority_buildings`
- `nhr.prediction_explanations`
- `nhr.demo_proof_events`
- `nhr.latest_model_run`
- `nhr.latest_priority_with_explanations`
- `nhr.latest_borough_priority_mix`

## Step 3 - Check Readiness

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk supabase-check
```

Expected result after `SUPABASE_DB_URL` is set:

- Schema exists.
- Tables exist.
- Views exist.
- Local payload exists.
- No `fail` rows in the readiness report.

Readiness report:

- [supabase_readiness.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/supabase/supabase_readiness.md)

## Step 4 - Publish Final Outputs

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk supabase-publish
```

Expected published payload:

- `1` model run
- `50` priority-building rows
- `50` explanation rows
- At least `5` demo proof events

Receipt:

- [supabase_publish_receipt.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/supabase/supabase_publish_receipt.md)

## Step 5 - Recheck

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk supabase-check
```

This should confirm that hosted Postgres now has the expected reporting objects and published rows.

## Step 6 - Run Class Demo Queries

Open Supabase SQL Editor and run:

- [06_supabase_demo_queries.sql](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/sql/06_supabase_demo_queries.sql)

In class, show these three outputs first:

1. `Latest published model run`
2. `Top 10 inspection-priority buildings with why_risky`
3. `Borough-level operational mix`

Then show the `demo_proof_events` query to connect the SQL layer back to the live API proof.

## If Something Fails

- If schema objects are missing, rerun `05_supabase_reporting_schema.sql`.
- If `SUPABASE_DB_URL` is missing, set it only in your terminal or in ignored `deploy/supabase.env`.
- If publish fails with auth or SSL errors, copy the Supabase `Session pooler` connection string again.
- If row counts are zero, run `make demo-proof` first, then run `make supabase-publish`.
- If final audit still warns about Supabase, confirm that `supabase_publish_receipt.md` exists after `make supabase-publish`.
