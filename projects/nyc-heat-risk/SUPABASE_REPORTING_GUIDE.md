# Optional SQL Reporting Appendix

Supabase is a managed backend platform built around Postgres. In this project it is intentionally scoped out of the required final demo because it does not improve the statistical model or the AWS/API proof.

The files in this section remain as an optional SQL appendix. They do not replace AWS, Docker, the trained model, the official-data ETL, or the local API proof.

## What This Optional Appendix Adds

- `SQL proof`: final model outputs can be queried from real Postgres tables, not just local CSV files.
- `Operational layer`: top-risk buildings, model run metadata, why-risky explanations, and demo proof events are stored in normalized tables.
- `Demo clarity`: if SQL is requested, a simple query can return the top priority buildings and the explanation for each one.

## What Supabase Does Not Do Here

- It does not train the model.
- It does not improve AUC, F1, calibration, or Precision@K.
- It does not replace AWS live deploy.
- It should not store the full 8.7M-row dense panel on the free tier.

## Architecture

```text
Official NYC/NOAA/CRE data
  -> Python ETL + feature engineering
  -> calibrated logistic ranking model
  -> inspection_priority_latest_day.csv + why_risky
  -> Supabase/Postgres reporting tables
  -> SQL demo, dashboard, Codex MCP queries
```

## Setup

1. Create a Supabase project.
2. Open the Supabase SQL Editor.
3. Run the schema in [05_supabase_reporting_schema.sql](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/sql/05_supabase_reporting_schema.sql).
4. Keep the database password local. Do not paste it into chat and do not commit it.

Use the live checklist when doing the real classroom/demo publish:

- [SUPABASE_LIVE_CHECKLIST.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/SUPABASE_LIVE_CHECKLIST.md)

```bash
export SUPABASE_DB_URL='postgresql://postgres.PROJECT_REF:YOUR_DATABASE_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require'
```

Alternatively, put the same value in a local ignored file:

```bash
cp deploy/supabase.env.example deploy/supabase.env
```

Then edit `deploy/supabase.env`. The Make targets load this file automatically, and `.gitignore` keeps it out of Git.

Use Supabase's session pooler connection string for this local publisher. It uses port `5432` on the `pooler.supabase.com` host and works well for this small batch upload.

5. First produce a local payload:

```bash
make supabase-dry-run
```

6. Check local payload and, if `SUPABASE_DB_URL` is set, check the database schema:

```bash
make supabase-check
```

This writes [supabase_readiness.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/supabase/supabase_readiness.md).

7. Then publish to Supabase:

```bash
make supabase-publish
```

Successful publish writes:

- [supabase_publish_receipt.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/supabase/supabase_publish_receipt.md)
- `nhr.model_runs`
- `nhr.daily_priority_buildings`
- `nhr.prediction_explanations`
- `nhr.demo_proof_events`

## Useful SQL Demo Queries

The full read-only demo script is here:

- [06_supabase_demo_queries.sql](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/sql/06_supabase_demo_queries.sql)

```sql
select
  inspection_priority_rank,
  building_id,
  borough,
  incident_address,
  round(model_probability::numeric, 4) as probability,
  round(equity_weighted_priority_score::numeric, 4) as equity_score,
  why_risky
from nhr.latest_priority_with_explanations
order by inspection_priority_rank
limit 10;
```

```sql
select *
from nhr.latest_borough_priority_mix;
```

```sql
select event_type, created_at
from nhr.demo_proof_events
order by created_at desc;
```

## Region Choice

For the real-world NYC story, choose a US region when possible because the operational users and AWS deploy scenario are NYC/US-centered. For a classroom demo from Turkey, a Europe region can feel faster, but it is less aligned with the project story. Region choice affects latency, not model quality.

## Security Rules

- Use a project-scoped connection and keep credentials local.
- Prefer read-only MCP mode for class/demo review.
- Never expose the Supabase service role key in frontend code.
- Do not connect Codex/MCP to sensitive production data.
- Keep full raw/panel data in local/AWS artifacts; publish only final priority outputs.
