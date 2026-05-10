# NYC Heating Complaint Risk Terraform

Bu klasör, proje için gereken minimum AWS kaynaklarını üretir:

- S3 artifact bucket
- ECR repository
- EKS service account için IRSA role

## Girdiler

Zorunlu alanlar:

- `region`
- `artifact_bucket`
- `ecr_repository`
- `cluster_oidc_provider_arn`
- `cluster_oidc_issuer_url`

Başlangıç için:

```bash
cp projects/nyc-heat-risk/infra/terraform/terraform.tfvars.example \
   projects/nyc-heat-risk/infra/terraform/terraform.tfvars
```

## Çalıştırma

```bash
cd projects/nyc-heat-risk/infra/terraform
terraform init
terraform plan
terraform apply
```

Apply sonrası önemli output’lar:

- `artifact_bucket`
- `ecr_repository_url`
- `irsa_role_arn`

Bu output’ları `deploy/aws.env` içine taşı.
