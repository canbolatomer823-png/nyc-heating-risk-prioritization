# AWS Values Guide

Bu dosya, `deploy/aws.env` içindeki her alanın AWS tarafında nereden bulunacağını hızlıca gösterir.

## AWS_REGION

Örnek:

```env
AWS_REGION=us-east-1
```

Nereden seçilir:

- EKS cluster’ı hangi region’da kuracaksan
- ECR repo hangi region’da olacaksa
- S3 bucket erişimini en çok hangi region’dan yapacaksan

Tavsiye:

- `us-east-1` ile başlamak en kolayı

## AWS_ACCOUNT_ID

Örnek:

```env
AWS_ACCOUNT_ID=123456789012
```

Nereden bulunur:

- AWS Console sağ üst account menüsü
- ya da `STS caller identity` çıktısı

## ARTIFACT_BUCKET

Örnek:

```env
ARTIFACT_BUCKET=omer-nyc-heat-risk-artifacts
```

Nereden bulunur:

- S3 Console
- bu proje için açacağın bucket adı

İçerisine şunlar yazılacak:

- `models/`
- `scored/`
- `priority/`
- `reports/`

## ARTIFACT_PREFIX

Örnek:

```env
ARTIFACT_PREFIX=nyc-heat-risk/latest
```

Bu değeri sen tanımlarsın.

Tavsiye:

- sabit latest yolu için `nyc-heat-risk/latest`
- versiyonlu istiyorsan `nyc-heat-risk/v1`

## ECR_REPOSITORY

Örnek:

```env
ECR_REPOSITORY=nyc-heat-risk-api
```

Nereden bulunur:

- ECR Console
- repository adını sen oluşturursun

## EKS_CLUSTER_NAME

Örnek:

```env
EKS_CLUSTER_NAME=nyc-heat-risk
```

Nereden bulunur:

- EKS Console
- cluster oluştururken verdiğin isim

## IRSA_ROLE_ARN

Örnek:

```env
IRSA_ROLE_ARN=arn:aws:iam::123456789012:role/nyc-heat-risk-irsa
```

Nereden bulunur:

- IAM Console > Roles
- EKS service account için oluşturduğun IAM role ARN

Minimum izinler:

- `s3:GetObject`
- `s3:PutObject`

En az şu yollar için:

- `s3://ARTIFACT_BUCKET/ARTIFACT_PREFIX/models/*`
- `s3://ARTIFACT_BUCKET/ARTIFACT_PREFIX/scored/*`
- `s3://ARTIFACT_BUCKET/ARTIFACT_PREFIX/priority/*`
- `s3://ARTIFACT_BUCKET/ARTIFACT_PREFIX/reports/*`

## IMAGE_TAG

Örnek:

```env
IMAGE_TAG=0.1
```

Bu değeri sen verirsin.

Tavsiye:

- `0.1`
- `2026-04-22`
- `git-short-sha`

## En kısa doldurma sırası

1. Region seç
2. S3 bucket oluştur
3. ECR repo oluştur
4. EKS cluster oluştur
5. IRSA role oluştur
6. `deploy/aws.env` dosyasını doldur
7. İstersen `bootstrap_stack.py --write-env` ile bucket/repo/irsa işini boto3 üzerinden otomatik kur
8. `prepare_deploy.sh` çalıştır
