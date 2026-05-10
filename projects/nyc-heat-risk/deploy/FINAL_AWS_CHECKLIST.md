# Final AWS Checklist

Bu checklist, proje kodu ve deploy iskeleti hazır olduktan sonra gerçek AWS hesabında son bağlamayı yapmak içindir.

## 1. Ön koşullar

- AWS credential aktif olmalı
- Docker daemon açık olmalı
- Hedef `EKS` cluster mevcut olmalı
- `kubectl` hedef EKS cluster'a bağlı olmalı
- `aws` CLI yoksa bile `boto3` tabanlı bootstrap çalışır; ama `docker login` ve `kubectl` için ilgili araçlar gerekir

İlk hızlı durum kontrolü:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk deploy-day-status
```

## 2. Env dosyasını gerçek değerlere getir

Dosya:

- [aws.env](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/aws.env)

Yarı otomatik doldurma:

```bash
bash /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/configure_aws_env.sh \
  --account-id 123456789012 \
  --region us-east-1 \
  --bucket omer-nyc-heat-risk-123456789012-us-east-1 \
  --eks-cluster nyc-heat-risk
```

Özellikle şu iki alan sentinel olmaktan çıkmalı:

- `AWS_ACCOUNT_ID`
- `IRSA_ROLE_ARN`

## 3. AWS kaynaklarını bootstrap et

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk aws-bootstrap
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk deploy-validate
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk aws-preflight
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk aws-preflight-release
```

Beklenen sonuç:

- STS hesabı env ile eşleşir
- S3 bucket erişilebilir ve region doğru olur
- ECR repository erişilebilir ve registry env hesabına ait olur
- EKS cluster `ACTIVE` durumda görünür
- IRSA role gerçekten vardır ve artifact prefix policy'si görünür
- `aws-preflight-release` ile `docker` ve `kubectl` binary kontrolleri de geçer
- `aws-bootstrap` sonrası IRSA role ARN env dosyasına yazılmış olur

Alternatif olarak tüm akışı tek komutta dry-run etmek için:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk release-dry-run
```

## 4. Deploy assetlerini hazırla

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk deploy-render
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk k8s-check
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk tfvars
```

Kontrol et:

- [deployment-summary.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/rendered/deployment-summary.md)
- [k8s/](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/rendered/k8s)
- [terraform.tfvars](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/infra/terraform/terraform.tfvars)

## 5. Artifact'leri S3'e bas

```bash
./.venv/bin/python /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/src/aws/publish_artifacts.py \
  --bucket YOUR_BUCKET \
  --prefix nyc-heat-risk/latest \
  --project-root /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk
```

## 6. API image'ını ECR'a gönder

Önce ECR login:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk ecr-login
```

Sonra image push:

```bash
docker build -f /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/Dockerfile \
  -t nyc-heat-risk-api /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk
docker tag nyc-heat-risk-api:latest YOUR_ACCOUNT.dkr.ecr.YOUR_REGION.amazonaws.com/nyc-heat-risk-api:0.1
docker push YOUR_ACCOUNT.dkr.ecr.YOUR_REGION.amazonaws.com/nyc-heat-risk-api:0.1
```

## 7. EKS'e uygula

Önce kubeconfig üret:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk kubeconfig
export KUBECONFIG=/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/generated-kubeconfig.yaml
```

Sonra manifestleri uygula:

```bash
kubectl apply -k /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/rendered/k8s
```

## 8. Son smoke test

- `GET /health`
- `GET /metadata`
- `GET /priorities/latest?top_n=5`
- `POST /score`

## 9. Athena

Şu dosyayı Athena'da çalıştır:

- [04_athena_external_tables.sql](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/rendered/sql/04_athena_external_tables.sql)

Başarılı kabul kriteri:

- API S3-backed artifact ile açılır
- priority list döner
- Athena external table sorgusu sonuç verir

Tek komutlu gerçek akış:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk release
```
