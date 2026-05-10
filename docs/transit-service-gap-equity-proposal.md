# Transit Service Gap Equity Risk

Bu belge, 15 günde teslim edilebilecek; ama yüzeysel kalmayacak kadar ciddi, gerçek veriyle çalışan ve sınıfta savunulabilir bir veri bilimi projesinin teknik omurgasını tanımlar.

## 1. Proje fikri

Klasik problem:
- "Otobüs gecikmesini tahmin edelim."

Bu proje ondan bilinçli olarak ayrılır:
- Sadece gecikmeyi tahmin etmez.
- Gecikmenin ve servis boşluğunun hangi hat, durak, saat ve mahallelerde sistematik olarak biriktiğini ölçer.
- Operasyonel risk ile toplumsal etkiyi aynı modelde ele alır.

Ana araştırma sorusu:

`Belirli bir hat-durak-zaman diliminde ciddi servis boşluğu veya aşırı gecikme riski nedir ve bu risk sosyal kırılganlığı yüksek mahallelerde orantısız biçimde yoğunlaşıyor mu?`

Bu nedenle proje üç çıktıyı aynı anda üretir:
- kısa vadeli operasyonel risk tahmini,
- hat ve durak bazlı açıklanabilir istatistiksel etki analizi,
- sosyal açıdan önceliklendirilmiş müdahale listesi.

## 2. Neden klişe değil

- Gecikme tahmininden bir adım öteye geçip `service gap burden` ölçüyor.
- Salt makine öğrenmesi gösterisi değil; yorumlanabilir istatistiksel model omurgası var.
- Mahalle kırılganlığı ile toplu taşıma güvenilirliğini birleştiriyor.
- Uygulama çıktısı doğrudan operasyon ekibinin kullanabileceği türden:
  - hangi duraklar riskli,
  - hangi saatlerde ek araç gerekir,
  - hangi bölgelerde hizmet eşitsizliği oluşuyor.

## 3. Gerçek problem tanımı

Otobüs işletmelerinde sadece ortalama gecikme önemli değildir. Asıl problem:
- belirli saatlerde iki aracın üst üste gelmesi,
- sonra uzun bir servis boşluğu oluşması,
- bunun da özellikle alternatif ulaşımı zayıf bölgelerde daha ağır hissedilmesidir.

Bu proje şu karara destek olur:
- "Yarın sabah hangi hat segmentlerinde yüksek servis boşluğu riski bekleniyor?"
- "Bu risk sosyal açıdan hassas bölgelerde birikiyor mu?"
- "Kaynak kısıtlıysa önce nereye müdahale edilmelidir?"

## 4. Veri kaynakları

Bu proje tamamen resmi ve gerçek veri kaynaklarına dayanır.

### 4.1 Transit verisi

Birincil kaynak:
- MTA Developer Resources: `https://www.mta.info/developers`
- MTA Bus Time API: `https://bt.mta.info/wiki/Developers/Index`

Amaç:
- gerçek zamanlı otobüs konum ve hareket verisi,
- hat ve durak bazlı operasyonel durum,
- GTFS static veriyle planlanan sefer yapısını eşleştirme.

Standartlar:
- GTFS Schedule Reference: `https://gtfs.org/documentation/schedule/reference/`
- GTFS Realtime Reference: `https://gtfs.org/documentation/realtime/reference/`

Not:
- 22 Nisan 2026 itibarıyla MTA resmi geliştirici sayfası gerçek zamanlı bus verisinin Bus Time API ile sağlandığını belirtmektedir.

### 4.2 Hava durumu verisi

Kaynak:
- NOAA Climate Data Online: `https://www.ncei.noaa.gov/cdo-web/`
- NOAA CDO API v2: `https://www.ncei.noaa.gov/cdo-web/webservices/v2`

Amaç:
- yağış,
- sıcaklık,
- rüzgar,
- ekstrem hava etkileri.

Not:
- NOAA belgeleri 22 Nisan 2026 itibarıyla API v2 kullanımını ve erişim token gereksinimini doğrulamaktadır.

### 4.3 Sosyal kırılganlık verisi

Güçlü seçenek:
- Census Community Resilience Estimates (CRE): `https://www.census.gov/data/developers/data-sets/community-resilience-estimates.html`

Tamamlayıcı seçenek:
- ACS API: `https://www.census.gov/programs-surveys/acs/data/data-via-api.html`

Amaç:
- mahalle veya tract bazlı sosyal kırılganlık,
- araçsız hane, gelir, yaşlı nüfus, engellilik, yoksulluk benzeri göstergeler,
- transit hizmet kalitesindeki bozulmanın kimleri daha çok etkilediğinin ölçülmesi.

Not:
- Census CRE geliştirici sayfası 29 Ocak 2026 tarihli 2024 veri çağrılarını göstermektedir.

## 5. Hedef değişken ve analitik çerçeve

Bu projede tek bir hedef değişken yerine iki katmanlı analiz önerilir.

### 5.1 Operasyonel hedef

İkili hedef:
- `high_service_gap_risk = 1`

Örnek tanım:
- planlanan headway ile gerçekleşen araç aralığı arasındaki fark belirli eşiği aşarsa,
- veya gecikme 10 dakika üzerindeyse,
- veya ardışık iki araç hareketi arasında kritik boşluk oluşursa risk 1 kabul edilir.

### 5.2 Etki hedefi

Sürekli skor:
- `equity_weighted_gap_score`

Örnek:
- servis boşluğu dakikası x mahallenin sosyal kırılganlık ağırlığı

Bu ikinci skor projeyi sıradan gecikme tahmininden ayıran ana unsurdur.

## 6. İstatistiksel omurga

Bu projeyi CV açısından güçlü yapan şey, makine öğrenmesi ile istatistiksel açıklamayı birlikte sunmasıdır.

### 6.1 Ana model

`Mixed-effects logistic regression`

Amaç:
- yüksek servis boşluğu riskinin olasılığını tahmin etmek.

Sabit etkiler:
- saat,
- hafta içi/hafta sonu,
- yağış,
- sıcaklık,
- geçmiş 30-60 dakika gecikme seviyesi,
- planlanan headway,
- durak tipi,
- rota yönü,
- sosyal kırılganlık skoru.

Rastgele etkiler:
- route_id,
- stop_id,
- borough veya tract kümesi.

Bu yapı neden doğru:
- transit verisi bağımsız gözlemlerden oluşmaz,
- aynı hatta ve aynı durakta tekrar eden örüntüler vardır,
- mixed-effects model bunu istatistiksel olarak daha dürüst ele alır.

### 6.2 Destekleyici analiz

`ANOVA / likelihood ratio test`

Amaç:
- hava durumu etkisi gerçekten anlamlı mı,
- sosyal kırılganlık eklendiğinde model anlamlı biçimde iyileşiyor mu,
- route bazlı farklılıklar sistematik mi.

### 6.3 Karşılaştırma modeli

`XGBoost` veya `LightGBM`

Amaç:
- tahmin gücünü benchmark etmek.

Kural:
- final anlatımda asıl vurgu yorumlanabilir modelde kalmalı,
- boosted trees sadece performans kıyası için kullanılmalı.

## 7. Hipotezler

Sınıfta savunmak için hipotezleri baştan net yazmak gerekir.

H1:
- Yağışlı hava koşullarında yüksek servis boşluğu riski artar.

H2:
- Planlanan headway uzun olan hatlarda varyans daha yüksektir.

H3:
- Geçmiş gecikme seviyesi arttıkça sonraki duraklardaki yüksek risk olasılığı artar.

H4:
- Sosyal kırılganlığı yüksek mahallelerde aynı operasyonel bozulma daha büyük toplumsal etkiye dönüşür.

H5:
- Sosyal kırılganlık değişkenlerinin eklenmesi modeli sadece açıklayıcı değil, politika açısından da daha anlamlı hale getirir.

## 8. Özellik mühendisliği

Önerilen feature set:
- `hour_of_day`
- `day_of_week`
- `is_peak_hour`
- `scheduled_headway_min`
- `actual_headway_min`
- `headway_gap_ratio`
- `rolling_route_delay_mean_30m`
- `rolling_route_delay_std_30m`
- `rolling_stop_gap_mean_60m`
- `precipitation`
- `temperature`
- `wind_speed`
- `route_direction`
- `stop_sequence_percent`
- `tract_resilience_score`
- `tract_zero_vehicle_rate`
- `tract_poverty_rate`

## 9. Başarı metrikleri

### 9.1 Tahmin metrikleri

- ROC AUC
- PR AUC
- F1-score
- Recall at top-k risky segments
- Brier score

### 9.2 Operasyonel metrikler

- en riskli yüzde 10 segment içinde gerçek bozulmaların yakalanma oranı
- risk sıralamasının hat planlaması için kullanılabilirliği

### 9.3 Etki metrikleri

- equity-weighted risk concentration
- yüksek kırılganlıklı bölgelerde hatalı negatif oranı

## 10. AWS mimarisi

Bu proje için minimal ama gerçekçi mimari yeterlidir.

### 10.1 Veri akışı

Akış:
- MTA realtime ingest
- S3 raw
- batch feature job
- S3 processed
- Athena SQL katmanı
- training job
- model artifact
- FastAPI inference

### 10.2 Kullanılacak servisler

- `S3`: raw, processed, models
- `Athena`: SQL analiz ve feature kontrolü
- `ECR`: container image registry
- `EKS`: ingest consumer, batch/train job, inference API
- `CloudWatch`: log ve metrik

İsteğe bağlı:
- `Glue Data Catalog`

15 gün içinde gereksiz büyümemek için şu servisleri ilk sürümde zorunlu tutma:
- SageMaker
- Kafka/MSK
- Redshift
- Step Functions

## 11. Docker ve Kubernetes rolü

Docker kullanım gerekçesi:
- ingest, train ve API servislerini taşınabilir kılmak
- lokal ve cloud ortamında aynı çalıştırma davranışını korumak

Kubernetes kullanım gerekçesi:
- API serving pod
- batch training job
- gerekirse cron tabanlı feature refresh

Sınıfta savunulacak mesaj:
- "Kubernetes kullandım çünkü ölçekleme ve iş ayrışması gerekiyordu; gösteriş olsun diye değil."

## 12. SQL tarafı

SQL bu projede dekoratif değil, merkezidir.

SQL ile yapılacaklar:
- ham olayların zaman penceresi bazlı özetlenmesi,
- route-stop-hour feature tabloları,
- model eğitim setinin üretilmesi,
- kalite kontrolleri,
- hata analizi tabloları.

Örnek sorgu hedefleri:
- en sık yüksek gap oluşan duraklar,
- yağışlı saatlerde route bazlı risk artışı,
- yüksek kırılganlıklı tract'lerde risk yoğunluğu.

## 13. R tarafı

R burada özellikle şu işler için değerlidir:
- mixed-effects model kurulumu,
- ANOVA ve significance testleri,
- diagnostik grafikler,
- Quarto final raporu.

Python tarafı:
- veri alma,
- feature engineering,
- API ve altyapı,
- benchmark model.

Bu hibrit kullanım, projeyi lisansüstü CV açısından daha güçlü yapar.

## 14. 15 günlük uygulanabilir teslim planı

### Gün 1
- proje kapsamını kilitle
- veri kaynaklarını doğrula
- MTA ve NOAA erişim anahtarlarını al

### Gün 2
- veri sözleşmesini yaz
- raw veri klasör yapısını oluştur
- ilk örnek ingest scriptini çalıştır

### Gün 3
- GTFS static ile realtime eşleme kur
- route, trip, stop anahtarlarını standardize et

### Gün 4
- SQL ile ilk feature tablosunu üret
- headway ve delay hesaplarını doğrula

### Gün 5
- EDA yap
- hedef değişken eşiklerini belirle

### Gün 6
- hava durumu zenginleştirmesini ekle
- eksik veri ve zaman hizalamasını çöz

### Gün 7
- CRE veya ACS tract verisini bağla
- equity skoru üret

### Gün 8
- mixed-effects logistic regression kur
- ilk katsayıları yorumla

### Gün 9
- ANOVA ve model karşılaştırmalarını yap
- anlamlı değişkenleri raporla

### Gün 10
- XGBoost benchmark modeli kur
- performans kıyası çıkar

### Gün 11
- Dockerfile'ları netleştir
- training ve API container'larını hazırla

### Gün 12
- EKS üstünde API ve train job ayağa kaldır
- S3 model artifact akışını test et

### Gün 13
- risk haritası veya tablo tabanlı dashboard hazırla
- örnek müdahale senaryosu üret

### Gün 14
- final rapor, metrik tabloları ve diyagramları temizle
- sınıf anlatımı için 30 dakikalık akış oluştur

### Gün 15
- prova yap
- teknik riskleri ve sınırlılıkları ezberle
- demo senaryosunu bitir

## 15. Final teslim çıktıları

Teslim sonunda şunlar olmalı:
- çalışan veri ingest pipeline'ı
- en az bir resmi veri kaynağından çekilmiş gerçek veri
- SQL ile üretilmiş feature tablosu
- mixed-effects regression sonuçları
- benchmark ML modeli
- Docker image'lar
- EKS üstünde çalışan API
- final teknik rapor
- 30 dakikalık sınıf sunum planı

## 16. Sınıfta savunulabilir ana katkı cümlesi

Bu proje, toplu taşıma gecikmesini tahmin etmekten daha ileri giderek, servis bozulmalarının sosyal olarak kırılgan bölgelerde nasıl yoğunlaştığını ölçen ve operasyon ekiplerinin sınırlı kaynakları nereye yönlendirmesi gerektiğini gösteren açıklanabilir bir risk sistemi sunar.

## 17. Riskler ve dürüst sınırlılıklar

- MTA bus realtime erişimi için API key gerekir.
- Gerçek zamanlı veride eksik kayıt olabilir.
- GTFS static ve realtime eşleştirmesi her zaman kusursuz değildir.
- Mahalle sosyoekonomik verisi bireysel neden-sonuç ispatı vermez; alan düzeyi ilişki sunar.
- 15 günlük sürede tam üretim sistemi değil, güçlü bir MVP hedeflenmelidir.

Bu sınırlılıklar projeyi zayıflatmaz. Tam tersine, ciddi bir veri bilimi çalışması yaptığını gösterir.
