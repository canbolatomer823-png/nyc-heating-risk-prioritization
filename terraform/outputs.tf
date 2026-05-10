output "data_lake_bucket" {
  value       = aws_s3_bucket.data_lake.bucket
  description = "Name of the S3 bucket hosting the data lake"
}

output "lambda_arn" {
  value       = aws_lambda_function.ingest.arn
  description = "ARN of the ingestion Lambda function"
}
