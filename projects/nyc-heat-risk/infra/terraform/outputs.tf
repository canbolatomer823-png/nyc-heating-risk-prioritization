output "artifact_bucket" {
  value       = aws_s3_bucket.artifacts.bucket
  description = "Artifact bucket name."
}

output "artifact_prefix" {
  value       = trim(var.artifact_prefix, "/")
  description = "Artifact prefix under the bucket."
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.api.repository_url
  description = "ECR repository URL for docker push."
}

output "irsa_role_arn" {
  value       = aws_iam_role.nhr_api_irsa.arn
  description = "IAM role ARN to place into the EKS service account annotation."
}
