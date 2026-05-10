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

locals {
  project_name         = "nyc-heat-risk"
  service_account_name = "nhr-api"
  namespace_name       = "nyc-heat-risk"
  artifact_prefix      = trim(var.artifact_prefix, "/")
  irsa_subject         = "system:serviceaccount:${local.namespace_name}:${local.service_account_name}"
}

resource "aws_s3_bucket" "artifacts" {
  bucket = var.artifact_bucket

  tags = {
    Project = local.project_name
    Owner   = var.owner
  }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "archive-scored-data"
    status = "Enabled"

    filter {
      prefix = "${local.artifact_prefix}/scored/"
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
  }
}

resource "aws_ecr_repository" "api" {
  name                 = var.ecr_repository
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project = local.project_name
    Owner   = var.owner
  }
}

data "aws_iam_policy_document" "irsa_assume_role" {
  statement {
    effect = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.cluster_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(var.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = [local.irsa_subject]
    }
  }
}

resource "aws_iam_role" "nhr_api_irsa" {
  name               = var.irsa_role_name
  assume_role_policy = data.aws_iam_policy_document.irsa_assume_role.json

  tags = {
    Project = local.project_name
    Owner   = var.owner
  }
}

data "aws_iam_policy_document" "nhr_api" {
  statement {
    sid    = "ArtifactBucketReadWrite"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.artifacts.arn}/${local.artifact_prefix}/*",
    ]
  }

  statement {
    sid    = "ArtifactBucketList"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.artifacts.arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["${local.artifact_prefix}/*"]
    }
  }
}

resource "aws_iam_role_policy" "nhr_api" {
  name   = "${var.irsa_role_name}-policy"
  role   = aws_iam_role.nhr_api_irsa.id
  policy = data.aws_iam_policy_document.nhr_api.json
}
