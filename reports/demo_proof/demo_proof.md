# Demo Proof Report

- Generated at: `2026-05-07 14:09:40 UTC`
- Local API: `http://127.0.0.1:50578`
- Artifact source: `local`
- Model type: `logistic_regression`
- Threshold: `0.2`
- Scored rows: `8753140`
- Priority rows loaded: `50`
- Latest priority date: `2025-05-30`

## What This Proves

- The FastAPI app can load the trained model bundle, scored CSV, priority CSV, and SQLite lookup artifact.
- The same project artifacts produce a top-N inspection priority list.
- The dashboard endpoint renders an inspector-facing HTML priority view.
- The record lookup endpoint can retrieve a real scored building-day record.
- The score endpoint returns probability, decision threshold, prediction, and a row-level `why_risky` explanation.

## Top Priority Example

- Rank: `1`
- Building ID: `65175`
- Borough: `BRONX`
- Address: `530 EAST 169 STREET`
- Probability: `0.9714179916416192`
- Equity-weighted score: `1.661028`
- Why risky: `Riski yukselten baslica sinyaller: prior complaint days=167, cumulative complaint history=645, heat sensor program flag=1.`

## Score Endpoint Example

- Probability: `0.401144`
- Threshold: `0.2`
- Prediction: `1`
- Why risky: `Riski yukselten baslica sinyaller: same-day complaints=4, 7-day complaint history=15, recent complaint recency=1.`

## Dashboard Proof

- Dashboard status: `ok`
- Dashboard HTML bytes: `6623`
- Dashboard file: `<project-root>/reports/demo_proof/dashboard.html`

## Files Created

- Health JSON: `<project-root>/reports/demo_proof/health.json`
- Metadata JSON: `<project-root>/reports/demo_proof/metadata.json`
- Priorities JSON: `<project-root>/reports/demo_proof/priorities_top5.json`
- Dashboard HTML: `<project-root>/reports/demo_proof/dashboard.html`
- Dashboard status JSON: `<project-root>/reports/demo_proof/dashboard_status.json`
- Record lookup JSON: `<project-root>/reports/demo_proof/record_lookup_top1.json`
- Score payload JSON: `<project-root>/reports/demo_proof/score_payload.json`
- Score response JSON: `<project-root>/reports/demo_proof/score_response.json`

## Class Demo Commands

```bash
make -C <project-root> demo-proof
cat <project-root>/reports/demo_proof/demo_proof.md
```

Optional live API view:

```bash
cat <project-root>/reports/demo_proof/priorities_top5.json
cat <project-root>/reports/demo_proof/score_response.json
```
