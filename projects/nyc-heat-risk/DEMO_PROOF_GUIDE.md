# Live Demo Proof Guide

Use this when you need to prove in class that the project is not only slides.

## One Command

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof
```

This starts the local FastAPI app on a temporary port, calls the main endpoints, writes proof JSON files, and creates:

- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/demo_proof.md`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/health.json`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/priorities_top5.json`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/record_lookup_top1.json`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/score_response.json`

## What To Show

1. Open `demo_proof.md`.
2. Show `health.json`: model, scored CSV, priority CSV, and SQLite lookup are loaded.
3. Show `priorities_top5.json`: the model produces a top-N inspection priority list.
4. Show `record_lookup_top1.json`: a real scored building-day can be retrieved by building/date.
5. Show `score_response.json`: a feature row returns probability, threshold, prediction, and `why_risky`.

## What To Say In Class

This proves the project has a working local serving layer. The operational output is not hand-written: the API loads the trained calibrated logistic model and official-data artifacts, then serves priority rankings and row-level explanations.

Hosted Supabase is intentionally scoped out because it does not improve the statistical model. If needed, the local SQL payload remains as an appendix, not as a main project claim.

The primary operational model is calibrated logistic ranking. GEE and Negative Binomial support statistical interpretation. GLMM is kept as a diagnostic mixed-effects check, not as the main performance claim.

## AWS Note

AWS live deploy is handled as a short-lived paid proof run. The project stores two evidence files after that run:

- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/aws_live_deploy_proof.md`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/aws_shutdown_proof.md`

Use the local `demo-proof` package for no-cost repeatable classroom proof. Use the AWS proof files to show that the same API was also served from a real AWS LoadBalancer with S3-backed artifacts, then shut down for cost control.
