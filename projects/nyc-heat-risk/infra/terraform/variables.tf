variable "region" {
  type        = string
  description = "AWS region for the heat risk deployment."
}

variable "owner" {
  type        = string
  description = "Owner tag."
  default     = "omer"
}

variable "artifact_bucket" {
  type        = string
  description = "S3 bucket used for published model and scoring artifacts."
}

variable "artifact_prefix" {
  type        = string
  description = "Stable prefix under the artifact bucket."
  default     = "nyc-heat-risk/latest"
}

variable "ecr_repository" {
  type        = string
  description = "ECR repository name for the API image."
}

variable "irsa_role_name" {
  type        = string
  description = "IAM role name used by the EKS service account."
  default     = "nyc-heat-risk-irsa"
}

variable "cluster_oidc_provider_arn" {
  type        = string
  description = "OIDC provider ARN for the target EKS cluster."
}

variable "cluster_oidc_issuer_url" {
  type        = string
  description = "OIDC issuer URL for the target EKS cluster."
}
