# Supply Chain Risk Intelligence – MVP Roadmap

This backlog aligns technical delivery with commercial traction so we can show value early while keeping the AWS footprint manageable. Sprints assume two-week cadence and a lean team (data engineer, ML engineer, data scientist, product lead).

## Stage 0 – Customer validation (week 0–2)
- Finalize 2–3 design partners, document their top KPIs (OEE, OTIF, mean time between failures).
- Inventory available data systems, latency needs, and integration constraints.
- Define success metrics (downtime % reduction, forecast accuracy lift, alert precision) and baseline collection.

## Stage 1 – Data landing zone (week 2–6)
- Terraform baseline: networking, S3 lake (raw/curated/analytics), KMS keys, IAM roles, Lake Formation permissions, logging buckets.
- Implement ingestion stubs:
  - IoT Core + sample device certs streaming into Kinesis + Firehose → S3 raw.
  - AWS Transfer Family SFTP endpoint writing batched ERP/WMS files to S3 raw.
  - Lambda ingestion template that normalizes CSV/JSON and stamps tenant metadata.
- Glue Crawler + Data Catalog registry for raw tables, Athena queries for quick validation.

## Stage 2 – Curated insights foundation (week 6–10)
- PySpark Glue job to cleanse ERP/WMS data, join with reference tables (plants, suppliers), emit curated Iceberg tables.
- Micro-batch aggregation job for IoT metrics (5-min windows) with anomaly scoring (MAD or Z-score) and SNS alerts via EventBridge.
- Step Functions orchestration with per-tenant parameters, CloudWatch dashboards, and error notifications.
- QuickSight proof-of-concept dashboard: live fulfillment funnel, equipment health, top at-risk POs.

## Stage 3 – Predictive risk services (week 10–14)
- SageMaker Feature Store + pipelines:
  - Downtime binary classifier (XGBoost) trained on IoT + maintenance logs.
  - Inbound ETA regression using historical carrier performance + weather data (AWS Data Exchange feed or public API via Lambda).
- Batch scoring workflow writing risk outputs to analytics layer and exposing via API Gateway (REST) + Cognito auth.
- AppSync/GraphQL schema for portal widgets (plant view, supplier scorecards) with multi-tenant resolvers.

## Stage 4 – Commercial readiness (week 14–18)
- Tenant provisioning automation (Step Functions + Service Catalog) and billing telemetry (CloudWatch metrics → Cost Explorer tagging).
- Hardening: Lake Formation row-level policies, audit logging, DR replication for S3 + Redshift snapshot strategy.
- Product polish: risk playbook templates, notification preferences, webhook connectors (ServiceNow/Jira/Slack).
- Go-to-market kit: demo dataset, scripted QuickSight story, ROI calculator, security/architecture one-pager.

## Backlog snapshot
| Sprint | Theme | Top backlog items |
| --- | --- | --- |
| 1 | Landing zone | Terraform baseline, IoT Core + Kinesis skeleton, Transfer Family config, ingestion Lambda template |
| 2 | Raw validation | Glue crawler, Athena checks, logging/monitoring, sample dashboards wired to raw metrics |
| 3 | Curated insights | PySpark cleansing job, IoT anomaly aggregation, Step Functions orchestration, QuickSight MVP |
| 4 | Predictive models | Feature Store setup, SageMaker pipelines, batch scoring + API Gateway, EventBridge alert routing |
| 5 | Commercial polish | Tenant provisioning, security hardening, ticketing/webhook connectors, GTM collateral |

Keep this backlog living; adjust scope after every design-partner review so engineering time maps directly to measurable KPI wins.
