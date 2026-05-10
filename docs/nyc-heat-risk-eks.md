# NYC Heating Complaint Risk on AWS + EKS

Bu belge, `projects/nyc-heat-risk/` projesinin gercek AWS proof akisini ozetler. Amac uzun sure acik kalan production sistemi kurmak degil; sinifta savunulabilir, timestamped, kisa sureli ve maliyet kontrollu bir cloud proof almaktir.

## Hedef Mimari

```text
Local ETL + modeling + reports
        |
        | publish_artifacts.py
        v
S3 artifact bucket
        |
        | FastAPI reads model / priority / lookup metadata
        v
Docker image -> ECR -> EKS Deployment
                          |
                          v
                    LoadBalancer URL
```

Bu tasarim neden savunulabilir:

- Model egitimi ve raporlama container icinde yapilmaz; release oncesi tamamlanmis artifactler S3'e konur.
- Runtime image kucuk kalir ve API S3-backed artifactlerle calisir.
- Live proof `/health`, `/metadata`, `/priorities/latest`, `/dashboard` ve `/score` endpointlerini gercek LoadBalancer URL uzerinden yakalar.
- Demo bittikten sonra EKS, nodegroup ve load balancer kapatilir; shutdown proof maliyet kontrolunu kanitlar.

## Kullanilan Dosyalar

- API: `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/src/api/app.py`
- Release script: `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/release_to_aws.sh`
- AWS env: `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/aws.env`
- K8s manifests: `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/k8s/`
- Live proof script: `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/src/aws/capture_live_deploy_proof.py`
- Shutdown proof script: `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/src/aws/capture_shutdown_proof.py`

## Release Sirasi

Proje klasorunden:

```bash
cd /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk
make deploy-day-status
make deploy-render
make k8s-check
make aws-preflight-release
make release
```

`make release` sirasiyla sunlari yapar:

- `deploy/aws.env` dogrulama
- S3/ECR/IRSA bootstrap
- artifact publish to S3
- Docker build/tag/push to ECR
- kubeconfig yazma
- `kubectl apply -k deploy/rendered/k8s`

## Live Proof Alma

LoadBalancer hostname geldikten sonra:

```bash
make aws-live-proof BASE_URL=http://YOUR_AWS_LOAD_BALANCER
```

Basarili proof dosyalari:

- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/aws_live_deploy_proof.md`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/aws_live_deploy/proof_summary.json`

Proof kriterleri:

- URL local degil, AWS LoadBalancer URL'si.
- `/health` status `ok`.
- `artifact_source.type` degeri `s3`.
- `model_type` degeri `logistic_regression`.
- Priority, dashboard ve score endpointleri gecerli cevap doner.

## Kapatma Proof'u

Demo bittikten sonra maliyetli kaynaklar silinir. Ardindan:

```bash
make aws-shutdown-proof
```

Basarili proof dosyalari:

- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/aws_shutdown_proof.md`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/aws_shutdown/shutdown_summary.json`

Shutdown proof su kaynaklarin kalmadigini kontrol eder:

- EKS cluster
- Matching Classic ELB
- Matching ELBv2 load balancer
- Project-tagged EC2 instance
- Project AutoScaling Group

## Sinifta Soylenecek Kisa Cumle

`Model artifactlerini S3'e koydum, API image'ini ECR'a bastim, FastAPI servisini EKS uzerinde LoadBalancer ile calistirdim, endpoint proof aldiktan sonra maliyet icin EKS/node/LB kaynaklarini kapattim. Bu yuzden elimde hem live deploy proof hem shutdown proof var.`

## Dikkat

- Silinen LoadBalancer URL'sini "su anda aktif" diye anlatma.
- HPA manifesti var, fakat ana kanit HPA degil; ana kanit S3-backed API'nin EKS uzerinde calismasi.
- S3/ECR/IAM artifactleri tekrar deploy icin bilerek durabilir; asil maliyetli kisim EKS node ve load balancer kaynaklaridir.
