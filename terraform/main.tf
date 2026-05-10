terraform {
  required_version = ">= 1.4.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "data_lake" {
  bucket = var.data_lake_bucket

  versioning {
    enabled = true
  }

  lifecycle_rule {
    id      = "raw-archive"
    enabled = true
    prefix  = "raw/"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }

  tags = {
    Project = "aws-analytics-pipeline"
    Owner   = var.owner
  }
}

resource "aws_iam_role" "lambda_ingest" {
  name = "lambda-ingest-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda-ingest-policy"
  role = aws_iam_role.lambda_ingest.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:PutObjectAcl"],
        Resource = ["${aws_s3_bucket.data_lake.arn}/raw/*"]
      },
      {
        Effect = "Allow"
        Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_lambda_function" "ingest" {
  function_name = "data-lake-ingest"
  role          = aws_iam_role.lambda_ingest.arn
  filename      = var.lambda_package
  handler       = "ingest_lambda.handler"
  runtime       = "python3.11"
  timeout       = 30

  environment {
    variables = {
      DATA_LAKE_BUCKET = aws_s3_bucket.data_lake.bucket
      SOURCE_URL       = var.source_url
    }
  }

  tags = {
    Project = "aws-analytics-pipeline"
  }
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.ingest.function_name}"
  retention_in_days = 30
}
