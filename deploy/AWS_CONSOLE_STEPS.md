# AWS Console Steps

Bu rehber, `22 Nisan 2026` itibarıyla `nyc-heat-risk` projesini gerçek AWS üzerinde ayağa kaldırmak için AWS Console içinde tıklayacağın adımları sıralar.

Ana hedef:

1. region seç
2. IAM access key hazırla
3. S3 bucket oluştur
4. ECR repository oluştur
5. EKS cluster oluştur
6. sonra local makinede deploy komutlarını çalıştır

Kaynaklar:

- [IAM user oluşturma](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html)
- [Access key güvenliği](https://docs.aws.amazon.com/console/general/access-keys-best-practices)
- [S3 bucket oluşturma](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket.html)
- [ECR private repository oluşturma](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html)
- [EKS Auto Mode cluster oluşturma](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-console.html)
- [EKS custom cluster oluşturma](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html)
- [EKS pricing](https://aws.amazon.com/eks/pricing/)
- [S3 pricing](https://aws.amazon.com/s3/pricing/)

## 1. Region seç

AWS Console sağ üstten region seç.

Bu proje için tavsiye:

- `us-east-1`

Sebep:

- repo varsayılanları buna göre hazır
- tek region kullanmak deploy hatasını azaltır

## 2. IAM access key hazırla

Not:

- Root kullanıcı ile çalışma.
- Ayrı bir IAM user kullan.
- Access key'i bana yazma.

Adımlar:

1. AWS Console'da `IAM` servisine gir.
2. Sol menüden `Users` seç.
3. `Create user` de.
4. Kullanıcı adı ver:
   - `nyc-heat-risk-admin`
5. Console erişimi şart değil; asıl gereken programmatic access için access key.
6. Kullanıcı oluşturulduktan sonra kullanıcı detayına gir.
7. `Security credentials` sekmesine geç.
8. `Create access key` seç.
9. Use case olarak local development uygun olan seçeneği seç.
10. `Access key ID` ve `Secret access key` değerlerini güvenli kaydet.

Hızlı ve pratik izin yaklaşımı:

- Demo/proje süresince bu user'a geniş izin ver.
- En kolay yol: `AdministratorAccess`
- Daha güvenli ama daha uğraştırıcı yol: IAM, S3, ECR, EKS için ayrı policy seti

Bu öneri bir tercih önerisidir; AWS dokümanı access key'leri dikkatli saklamanı ve root key kullanmamanı öneriyor.

## 3. S3 bucket oluştur

Adımlar:

1. `S3` servisine gir.
2. `Create bucket` de.
3. Bucket adı ver:
   - `omer-nyc-heat-risk-artifacts`
   - eğer doluysa sonuna sayı ekle
4. Region:
   - `us-east-1`
5. `Block all public access` açık kalsın.
6. Versioning açabilirsin; şart değil ama iyi olur.
7. Varsayılan encryption açık kalsın.
8. `Create bucket` de.

Bu bucket proje artifact'leri için kullanılacak:

- model bundle
- scored output
- priority output
- reports

## 4. ECR repository oluştur

Adımlar:

1. `Amazon ECR` servisine gir.
2. `Private repositories` seç.
3. `Create repository` de.
4. Repository adı:
   - `nyc-heat-risk-api`
5. Scan on push açık kalabilir.
6. `Create` de.

Bu repository API container image'ını tutacak.

## 5. EKS cluster oluştur

Burada iki yol var:

- daha hızlı yol: `EKS Auto Mode`
- daha kontrollü yol: `Custom configuration`

Bu proje için en hızlı mantıklı yol:

- `EKS Auto Mode`

Adımlar:

1. `Amazon EKS` servisine gir.
2. `Create cluster` de.
3. `Quick configuration` açık kalsın.
4. Cluster adı ver:
   - `nyc-heat-risk`
5. Node role için AWS'nin önerdiği rolü oluşturmasına izin ver.
6. VPC kısmında:
   - varsa uygun VPC seç
   - yoksa `Create VPC` ile yeni VPC oluştur
7. Subnet seçiminde varsayılanları koru.
8. `Create cluster` de.

Beklenen süre:

- yaklaşık `15 dakika`

Önemli maliyet notu:

- `22 Nisan 2026` itibarıyla AWS EKS FAQ ve pricing sayfaları EKS cluster için saatlik ücret olduğunu söylüyor.
- Yani cluster açık kaldığı sürece maliyet oluşur.
- İşin bitince kapatmayı unutma.

## 6. EKS cluster adı ve account id'yi not al

Sonra local tarafta şunlar gerekecek:

- `AWS_ACCOUNT_ID`
- `EKS_CLUSTER_NAME`

Account ID yeri:

- sağ üst hesap menüsü

Cluster adı:

- EKS cluster detay ekranı

## 7. Local makinede credential dosyasını doldur

AWS Console'dan aldığın access key ile kendi makinede:

- `~/.aws/credentials`
- `~/.aws/config`

Dosya şablonları:

- [aws-credentials.example](<project-root>/deploy/aws-credentials.example)
- [aws-config.example](<project-root>/deploy/aws-config.example)

## 8. Local tarafta çalıştıracağımız komutlar

AWS Console tarafı tamamlanınca ben bunları çalıştıracağım:

```bash
make -C <project-root> aws-bootstrap
make -C <project-root> deploy-validate
make -C <project-root> aws-preflight
make -C <project-root> deploy-render
make -C <project-root> k8s-check
make -C <project-root> ecr-login
make -C <project-root> kubeconfig
```

Sonra:

- artifact'leri S3'e basacağız
- Docker image'ını ECR'a push edeceğiz
- `kubectl apply -k ...` ile EKS'e geçeceğiz

## 9. En kısa pratik sıra

AWS sitesine girdikten sonra sadece bunu izle:

1. Region'ı `us-east-1` yap
2. IAM user oluştur
3. Access key üret
4. S3 bucket oluştur
5. ECR repository oluştur
6. EKS cluster oluştur
7. Account ID ve cluster adını not et
8. Access key'i local `~/.aws/credentials` içine koy
9. Buraya dön ve `hazır` yaz
