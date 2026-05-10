# Study Guide

The idea is to learn by delivering a working slice each session. Treat every bullet as a mini-project and commit your work frequently.

## Session 1 – Local Understanding
- Read the dataset README or Kaggle description and note target metrics.
- Use `notebooks/exploration-template.ipynb` to inspect distributions and null values.
- List the top 3 data quality risks you must fix in Glue.

## Session 2 – Infrastructure
- Review `terraform/main.tf` and map each resource to the architecture diagram.
- Customize `terraform.tfvars`, then run `terraform plan` to see the diff.
- Deploy only the S3 bucket first by commenting other resources so you can validate IAM policies incrementally.

## Session 3 – Ingestion
- Update `lambda/ingest_lambda.py` with the real dataset URL.
- Run `pytest` (create simple tests) or execute the module locally using the `__main__` block.
- Package and deploy via Terraform; trigger the Lambda manually in the AWS Console to confirm data lands in S3.

## Session 4 – Transformation
- Configure a Glue Crawler for the raw prefix and inspect the schema in the Data Catalog.
- Modify `glue/cleaning_job.py` to implement actual cleaning rules (type casting, filtering, feature engineering).
- Run the job and validate the Parquet output with Athena.

## Session 5 – Modeling
- Choose a predictive question (classification or regression) and configure SageMaker Autopilot.
- Capture metrics such as accuracy, ROC AUC, or RMSE in a Markdown report.
- Decide if you need a batch transform or real-time endpoint.

## Session 6 – Visualization and Storytelling
- Build a QuickSight dashboard using the Athena data source.
- Annotate visuals with business-friendly titles and callouts.
- Record a short Loom-style walkthrough in Turkish to show stakeholders.

## Session 7 – Polish and Reflection
- Add cost tags and CloudWatch alarms.
- Update the README with results, lessons learned, and future work.
- Prepare a two-minute pitch describing the problem, solution, and impact.

Learning is compounding—document everything so you can teach it back later.
