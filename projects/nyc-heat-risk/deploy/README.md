# AWS Deploy Folder

Bu klasör, `nyc-heat-risk` projesinin AWS/EKS dağıtım değerlerini tek yerden doldurmak için var.

## 0. Credential

Bu repo secrets tutmaz. AWS erişimini kendi makinede standart dosyalarla ver:

- `~/.aws/credentials`
- `~/.aws/config`

Örnek şablonlar:

- [aws-credentials.example](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/aws-credentials.example)
- [aws-config.example](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/aws-config.example)
- [AWS_CONSOLE_STEPS.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/AWS_CONSOLE_STEPS.md)

## 1. Env dosyasını oluştur

Örneği kopyala:

```bash
cp projects/nyc-heat-risk/deploy/aws.env.example projects/nyc-heat-risk/deploy/aws.env
```

Sonra şu alanları doldur:

- `AWS_REGION`
- `AWS_ACCOUNT_ID`
- `ARTIFACT_BUCKET`
- `ARTIFACT_PREFIX`
- `ECR_REPOSITORY`
- `EKS_CLUSTER_NAME`
- `IRSA_ROLE_ARN`
- `IMAGE_TAG`

Not:

- Repo içinde boş kalmaması için varsayılan bir [aws.env](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/aws.env) bıraktım.
- Bu dosyada `AWS_ACCOUNT_ID=000000000000` ve benzeri sentinel değerler var.
- Gerçek deploy öncesi bunları düzeltmen gerekir.

## 2. Önce doğrula

```bash
./.venv/bin/python projects/nyc-heat-risk/src/aws/validate_deploy_env.py \
  --env-file projects/nyc-heat-risk/deploy/aws.env
```

## 3. Render et

```bash
./.venv/bin/python projects/nyc-heat-risk/src/aws/render_deployment_assets.py \
  --env-file projects/nyc-heat-risk/deploy/aws.env \
  --project-root projects/nyc-heat-risk \
  --output-dir projects/nyc-heat-risk/deploy/rendered
```

## 4. Çıktılar

Render sonrası burada oluşur:

- `projects/nyc-heat-risk/deploy/rendered/k8s/`
- `projects/nyc-heat-risk/deploy/rendered/sql/04_athena_external_tables.sql`
- `projects/nyc-heat-risk/deploy/rendered/deployment-summary.md`

Bu sayede placeholder’ları tek tek elle değiştirmek zorunda kalmazsın.

## 5. Tek komut

İstersen iki adımı birleştir:

```bash
bash projects/nyc-heat-risk/deploy/prepare_deploy.sh
```

Her dizinden çalışacak kısa yol:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk deploy-render
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk k8s-check
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk deploy-day-status
```

Alanların AWS’te nereden bulunacağını görmek için:

- [AWS_ENV_SETUP.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/AWS_ENV_SETUP.md)
- [AWS_VALUES_GUIDE.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/AWS_VALUES_GUIDE.md)
- [FINAL_AWS_CHECKLIST.md](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/FINAL_AWS_CHECKLIST.md)

Ek araçlar:

- `bash projects/nyc-heat-risk/deploy/configure_aws_env.sh --account-id 123456789012`
- `./.venv/bin/python projects/nyc-heat-risk/src/aws/preflight_check.py --env-file projects/nyc-heat-risk/deploy/aws.env`
- `./.venv/bin/python projects/nyc-heat-risk/src/aws/preflight_check.py --env-file projects/nyc-heat-risk/deploy/aws.env --require-docker --require-kubectl`
- `./.venv/bin/python projects/nyc-heat-risk/src/aws/render_tfvars.py --env-file projects/nyc-heat-risk/deploy/aws.env`
- `./.venv/bin/python projects/nyc-heat-risk/src/aws/bootstrap_stack.py --env-file projects/nyc-heat-risk/deploy/aws.env --write-env`
- `./.venv/bin/python projects/nyc-heat-risk/src/aws/ecr_login.py --env-file projects/nyc-heat-risk/deploy/aws.env`
- `./.venv/bin/python projects/nyc-heat-risk/src/aws/write_kubeconfig.py --env-file projects/nyc-heat-risk/deploy/aws.env --output projects/nyc-heat-risk/deploy/generated-kubeconfig.yaml`
- `bash projects/nyc-heat-risk/deploy/run_local_smoke_test.sh`
- `bash projects/nyc-heat-risk/deploy/check_k8s_manifests.sh`

Not:

- `projects/...` ile başlayan örnekler workspace kökünden çalıştırmak içindir.
- `make -C ...` örnekleri ise bulunduğun dizinden bağımsızdır.
## One-command release

Gercek AWS hesabinda env dosyasi doldurulduktan sonra tum publish/build/apply akisi tek komutta kosabilir:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk release
```

Sadece komutlari gormek icin:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk release-dry-run
```

Canli apply oncesi en sert yerel kontrol:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk aws-preflight-release
```

Deploy gunu oncesi hizli hazirlik ozeti:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk deploy-day-status
```

Bu komut:

- `aws.env` var mi bakar
- `~/.aws/credentials` ve `~/.aws/config` var mi bakar
- Docker daemon acik mi kontrol eder
- `kubectl` var mi bakar
- `aws.env` hala sentinel deger tasiyor mu kontrol eder
