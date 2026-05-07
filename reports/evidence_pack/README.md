# Demo Evidence Pack

- Generated at: `2026-05-05 18:52:38 UTC`
- Purpose: prove in class that the project is reproducible, queryable, and runnable.

## Fast Proof Order

1. Run the local proof: `make -C <project-root> demo-proof`
2. Open the dashboard: `http://127.0.0.1:8000/dashboard` after starting `make serve`.
3. Show API JSON: `/health`, `/metadata`, `/priorities/latest?top_n=5`, `/score`.
4. Show AWS proof files: `aws_live_deploy_proof.md` and `aws_shutdown_proof.md`.
5. Show final audit: `make -C <project-root> final-audit`.

## What To Say In One Sentence

I built a real-data decision-support prototype that ranks NYC residential buildings by next-day heating/hot-water complaint risk and explains why each building is prioritized.

## Core Numbers To Show

- Held-out ROC AUC: `0.8036`
- Held-out Precision@50: `0.2743`
- Held-out Lift@50: `47.3438`
- OOT ROC AUC: see out-of-time validation report.
- Dense panel: see data card.

## Evidence Files

- Final audit: [final_project_audit.md](<project-root>/reports/final_project_audit.md)
- Demo proof: [demo_proof.md](<project-root>/reports/demo_proof/demo_proof.md)
- AWS live proof: [aws_live_deploy_proof.md](<project-root>/reports/aws_live_deploy_proof.md)
- AWS shutdown proof: [aws_shutdown_proof.md](<project-root>/reports/aws_shutdown_proof.md)
- Model card: [model_card.md](<project-root>/reports/model_card.md)
- Data card: [data_card.md](<project-root>/reports/data_card.md)
- Dashboard visual summary: [dashboard_summary.png](<project-root>/reports/evidence_pack/dashboard_summary.png)
- Final slides with QR: [output_with_qr.pptx](<project-root>/outputs/nyc-heating-risk-final/output_with_qr.pptx)
- Final slides PDF with QR: [output_with_qr.pdf](<project-root>/outputs/nyc-heating-risk-final/output_with_qr.pdf)
- Brochure PDF: [output.pdf](<project-root>/outputs/nyc-heating-brochure-final/output.pdf)
- Brochure QR image: [brochure_qr.png](<project-root>/outputs/nyc-heating-brochure-final/brochure_qr.png)
- Record lookup DB: [record_lookup.sqlite](<project-root>/data/windows/heat_season_2024_10_01_2025_05_31/processed/record_lookup.sqlite)

## Honest Status

- Core analytics and local API proof are ready.
- Hosted Supabase is scoped out; optional SQL payload files remain as an appendix only.
- AWS has timestamped live proof and shutdown proof; recreate the endpoint only if a currently reachable URL is required on demo day.
- Brochure QR uses an S3 presigned URL; regenerate or refresh it if the presentation date moves after its expiry.
