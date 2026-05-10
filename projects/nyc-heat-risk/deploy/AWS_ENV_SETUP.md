# AWS Env Setup

This step fills non-secret deployment values in `deploy/aws.env`.

It does not store AWS access keys. Credentials stay in:

- `~/.aws/credentials`
- `~/.aws/config`

## 1. Find Your Account ID

AWS Console:

- Open the account menu in the top-right corner.
- Copy the 12-digit account ID.

## 2. Pick Region

Recommended:

```env
AWS_REGION=us-east-1
```

Use one region for S3, ECR, and EKS to reduce deployment errors.

## 3. Write `aws.env`

Replace `123456789012` with your real AWS account ID:

```bash
bash /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/configure_aws_env.sh \
  --account-id 123456789012 \
  --region us-east-1 \
  --bucket omer-nyc-heat-risk-123456789012-us-east-1 \
  --eks-cluster nyc-heat-risk
```

The bucket name must be globally unique. If AWS says the bucket name is taken, use:

```bash
--bucket omer-nyc-heat-risk-123456789012-us-east-1-v2
```

## 4. Check Readiness

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk deploy-day-status
```

Expected after env setup:

- Docker daemon reachable
- `AWS_ACCOUNT_ID` no longer `000000000000`
- `IRSA_ROLE_ARN` no longer contains `000000000000`
- AWS credentials may still be missing until the next step

## 5. Next Step

After this, configure credentials in `~/.aws/credentials` and `~/.aws/config`.

Do not paste access keys into project files, slides, docs, or chat logs.
