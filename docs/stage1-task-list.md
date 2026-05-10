# Stage 1 Görev Listesi (Hafta 2–6) – Veri İniş Katmanı

Bu liste, Stage 1 hedefleri olan temel AWS altyapısı + ham veri giriş boru hatlarını ayrıntılandırır. Her görevin çıktısı, test kriteri ve sorumlu profili belirtilmiştir.

## 1. Terraform/Altyapı
| Görev | Açıklama | Çıktı | Onay/Test |
| --- | --- | --- | --- |
| tf-bootstrap | Backend (S3 + DynamoDB) ve ortak tag’ler | `terraform/backend.tf`, `providers.tf` | `terraform init` başarılı |
| Ağ + güvenlik | VPC, özel/ortak subnet’ler, NAT, güvenlik grupları | `terraform/modules/network` | `terraform plan` ile CIDR doğrulaması |
| S3 data lake | `raw/curated/analytics` prefix’leri, lifecycle politikaları, KMS CMK | `terraform/modules/data_lake` | AWS CLI ile bucket + policy kontrolü |
| IAM + Lake Formation | Roles/policies (Glue, Lambda, SageMaker, QuickSight), LF kayıtları | `terraform/modules/iam` | `aws iam simulate-principal-policy` |

## 2. IoT + Streaming ingest
| Görev | Açıklama | Çıktı | Test |
| --- | --- | --- | --- |
| IoT Core setup | Sertifika + policy + thing template | `terraform/modules/iot` | Test cihazı ile MQTT publish |
| Kinesis + Firehose | IoT stream’den Firehose’a, oradan S3 raw’a yönlendirme | `terraform/modules/streaming` | Kinesis test kaydı → S3’de Parquet |
| CloudWatch log grupları | IoT Rule, Lambda, Firehose log retention ayarı | Terraform kaydı | Log’ların oluşması |

## 3. ERP/WMS ingest
| Görev | Açıklama | Çıktı | Test |
| --- | --- | --- | --- |
| Transfer Family | SFTP sunucusu, kullanıcı, IAM role, home directory | Terraform | SFTP upload → S3 raw |
| Ingestion Lambda | CSV/JSON normalize eden Python şablonu (tenant tag) | `lambda/ingestion_handler.py` | Lokal pytest + örnek dosya akışı |
| EventBridge rule | Dosya yüklenince Lambda tetikleyen kural | Terraform | Test event → Lambda invocation |

## 4. Şema & doğrulama
| Görev | Açıklama | Çıktı | Test |
| --- | --- | --- | --- |
| Glue Crawler | `raw_iot`, `raw_erp` tablosu | Terraform/console config | Crawler run success |
| Athena doğrulama | Örnek SQL ile veri kontrolü | `docs/queries/raw-validation.sql` | Sorgu sonucu örnek çıktı |
| Observability | CloudWatch dashboard + alarm (Firehose error rate) | Terraform | Alarm test (manüel) |

## 5. Dokümantasyon/DevX
- README güncellemesi: Stage 1 kurulum adımları.
- Runbook: IoT cihaz ekleme, SFTP kullanıcı oluşturma.
- Tasarım kararları: IAM/LF yetki modeli, veri katalog yapısı.

Bu görevlerin kapanmasıyla Stage 1 “Go/No-Go” kriterleri: (1) IoT + ERP örnek verisi raw katmanına akıyor, (2) Glue/Athena ile okunabilir, (3) Temel izleme ve güvenlik artefaktları tamam.
