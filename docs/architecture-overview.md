# Supply Chain Risk Intelligence – Architecture Overview

This system turns siloed supply-chain telemetry into proactive risk alerts. Core personas (plant ops, logistics planners, exec stakeholders) receive one live view of asset health, supplier KPIs, and inbound shipment ETAs so they can avoid downtime and stock-outs.

## High-level architecture

```
          ┌───────────────────── Ingestion ──────────────────────┐
┌────────────┐   ┌────────────┐   ┌───────────────┐   ┌─────────┐
│ Plant/IoT  │→→│ AWS IoT Core│→→│ Kinesis Streams│→→│ Firehose │
└────────────┘   └────────────┘   └───────────────┘   └────┬────┘
                                                           │
┌────────────┐   ┌────────────┐   ┌───────────────┐        │
│ ERP / WMS  │→→│ AWS Transfer│→→│ Lambda ingest  │────────┘
└────────────┘   └────────────┘   └───────────────┘
                                                           ▼
                        ┌───────────────────────────────────────────────┐
                        │                S3 Data Lake                    │
                        │ raw / curated / analytics prefixes (Iceberg)   │
                        └──────────────┬───────────────────────┬────────┘
                                       │                       │
                         ┌─────────────▼──────────┐   ┌────────▼────────┐
                         │ AWS Glue ETL + Catalog │   │ Step Functions  │
                         │ (PySpark + CDC merges) │   │ orchestrations  │
                         └─────────────┬──────────┘   └────────┬────────┘
                                       │                       │
                     ┌─────────────────▼──────────┐   ┌────────▼─────────┐
                     │ SageMaker Pipelines + FS   │   │ EventBridge +    │
                     │ (ETA + downtime models)    │   │ SNS alerts        │
                     └──────────────┬─────────────┘   └────────┬─────────┘
                                    │                         │
                       ┌────────────▼────────────┐     ┌───────▼────────────┐
                       │ Redshift Serverless /   │     │ API Gateway +       │
                       │ Athena / QuickSight     │     │ AppSync tenant APIs │
                       └─────────────────────────┘     └────────────────────┘
```

## Data flow

1. **Telemetry capture** – Machine and line-level signals enter AWS IoT Core using MQTT certificates. Rule actions push the streams into Kinesis Data Streams for sub-second buffering. Logistics/WMS/ERP data lands via AWS Transfer Family (SFTP) or AppFlow connectors and is normalized through Lambda ingestion functions.
2. **Landing zone** – All raw assets are versioned in an S3 data lake organized by `business_domain/source/layer`. Firehose delivers IoT data in Parquet batches. Ingestion Lambdas tag data with plant, supplier, and tenant identifiers to support isolation.
3. **Processing + catalog** – AWS Glue jobs (Spark) handle schema evolution, join telemetry with master data, calculate KPIs (Overall Equipment Effectiveness, supplier OTIF), and emit Iceberg tables. Glue Crawlers/register scripts keep the Data Catalog synchronized for Athena/Redshift Spectrum.
4. **Workflow control** – AWS Step Functions orchestrate daily batch runs (ERP snapshots), micro-batch IoT aggregations, and ML retraining. EventBridge rules trigger ad-hoc reruns or anomaly investigations.
5. **ML + analytics** – SageMaker Pipelines consume curated features from Feature Store to train: (a) downtime probability classifier, (b) ETA regression for inbound POs, (c) anomaly detection for IoT sensors. Model outputs are written back to the analytics layer and surfaced via API + BI.
6. **Serving layer** – Redshift Serverless powers multi-tenant dashboards in QuickSight (embedded in the customer portal). An AppSync or API Gateway + Lambda tier exposes risk scores, recommended actions, and webhook notifications. SNS/SES integrate with ticketing suites (ServiceNow/Jira).

## Operational guardrails

- **Tenant isolation:** Separate KMS keys + IAM access per customer, AWS Lake Formation row/column filters, and Cognito user pools with group-based entitlements.
- **Observability:** CloudWatch metrics, Glue job run logs, EMF structured logging from Lambdas, distributed tracing via X-Ray on orchestration paths.
- **Cost controls:** S3 lifecycle policies (raw → Glacier), Kinesis On-demand for burst handling, and automated SageMaker endpoint scaling (or batch transforms for non-real-time use cases).
- **Resilience:** Cross-region replication for critical S3 prefixes, multi-AZ Redshift, and fallback notification channels when QuickSight/Redshift is degraded.

Keep this diagram close while authoring Terraform/IaC so each component maps to a concrete AWS resource and business capability.
