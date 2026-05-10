# Terraform Bootstrap

This module provisions the foundational resources required by the analytics pipeline.

## Prerequisites

1. Install Terraform 1.4 or later.
2. Package the Lambda function:
   ```bash
   cd ../lambda
   zip ../terraform/build.zip ingest_lambda.py
   ```
3. Create a terraform.tfvars file with your variables:
   ```hcl
   data_lake_bucket = "data-lake-omer"
   lambda_package   = "build.zip"
   source_url       = "https://api.publicapis.org/random"
   ```

## Workflow

1. Initialize providers and modules:
   ```bash
   terraform init
   ```
2. Preview changes:
   ```bash
   terraform plan -out=tfplan
   ```
3. Apply the infrastructure:
   ```bash
   terraform apply tfplan
   ```

Observe how each resource maps to the architecture diagram:
- `aws_s3_bucket.data_lake` corresponds to the raw/processed/analytics layers.
- `aws_lambda_function.ingest` handles the ingestion step of the pipeline.
- IAM roles restrict the Lambda function to the minimal required permissions.

Destroy the environment when finished experimenting:
```bash
terraform destroy
```
