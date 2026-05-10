variable "region" {
  type        = string
  description = "AWS region for all resources"
  default     = "eu-central-1"
}

variable "data_lake_bucket" {
  type        = string
  description = "Globally unique S3 bucket name for the data lake"
}

variable "owner" {
  type        = string
  description = "Tag identifying the project owner"
  default     = "omer"
}

variable "lambda_package" {
  type        = string
  description = "Path to the zipped Lambda package"
}

variable "source_url" {
  type        = string
  description = "Public dataset endpoint used by the Lambda ingestion function"
}
