# NYC Heating and Hot Water Complaint Risk Prioritization

Bu belge, projeyi gerçek teslim edilen haliyle tanımlar.

## 1. Proje adı

Resmi ad:

- `NYC Heating and Hot Water Complaint Risk Prioritization`

Kısa sınıf adı:

- `NYC Heating Complaint Risk`

## 2. Tek cümlelik tanım

New York'ta hangi konut binalarının ertesi gün `heat/hot water` şikayeti üretme riskinin yüksek olduğunu resmi açık verilerle tahmin eden ve denetim önceliği çıkaran bir `building-day` karar destek prototipi.

## 3. Problem çerçevesi

Bu proje yaz sıcak dalgası analizi değildir.

Mevcut prototip şu problemi çözer:

- soğuk hava, bina geçmişi ve ihlal örüntüleri birlikteyken
- hangi binalar ertesi gün `heat/hot water` şikayeti üretmeye daha yatkın?

Bu çerçeve NYC'nin resmi `Heat Season` ve yıl boyu sıcak su yükümlülüğü ile uyumludur.

## 4. Neden güçlü

- tamamı resmi veri
- gerçek kamu problemi
- sadece dashboard değil, risk skoru ve öncelik listesi üretiyor
- ETL + istatistik + API + deploy hattı bir arada
- sınıfta savunulabilir

## 5. Mevcut veri kapsamı

Şu anki aktif final build:

- dönem: `2024-10-01 -> 2025-05-31`
- complaint kayıtları: `282,296`
- benzersiz bina: `36,170`
- dense `building-day` satırı: `8,789,310`
- tract-level `CRE` coverage: yaklaşık `%99.21`

Legacy `2025-01` prototip artefact'leri disk üzerinde durur, ama final teslim kapsamı bu heat-season penceresidir.

## 6. Resmi veri kaynakları

- `311 Service Requests from 2010 to Present` (`erm2-nwe9`)
- `Housing Maintenance Code Complaints and Problems` (`ygpa-z7cr`)
- `Buildings Subject to HPD Jurisdiction` (`kj4p-ruqc`)
- `Multiple Dwelling Registrations` (`tesw-yqqr`)
- `Housing Maintenance Code Violations` (`wvxf-dwi5`)
- `Buildings Selected for the Heat Sensor Program` (`h4mf-f24e`)
- `NOAA GSOD`

Not:

- `Census CRE` tract-level olarak dense panele entegre edildi
- priority list equity-weighted score ile üretiliyor

## 7. Analiz birimi

Ana birim:

- `building-day`

Neden:

- müdahale bina bazında yapılıyor
- hava günlük değişiyor
- complaint davranışı zaman içinde kümeleniyor

## 8. Hedefler

### 8.1 İkili operasyonel hedef

- `next_day_positive_flag`
- ertesi gün en az bir complaint olacak mı?

### 8.2 Sayım hedefi

- `next_day_complaint_count`
- ertesi gün complaint hacmi ne olur?

## 9. Gerçekte kullanılan modeller

Bu kısmı özellikle dürüst bırak:

- kural tabanlı baseline
- `logistic regression` benchmark
- `GEE logistic` clustered inference modeli
- `Binomial GLMM` random-intercept diagnostic modeli
- `Negative Binomial` count modeli

## 10. Gerçek feature blokları

- günlük complaint sayıları
- rolling complaint history
- recent complaint flag
- geçmiş complaint yoğunluğu
- registration aktiflik sinyali
- Heat Sensor Program sinyali
- unit count proxy
- as-of-date violation feature'ları
- günlük hava değişkenleri

Önemli not:

- violation feature’ları temporal leakage olmayacak şekilde complaint tarihine kadar sınırlandı

## 11. Çıktılar

Ana çıktılar:

- model raporları
- coefficient tabloları
- inspection priority list
- FastAPI scoring API
- PowerPoint sunumu
- AWS deploy iskeleti

## 12. Başarı ölçütü

Bu projede başarı sadece F1 değildir.

Başarı şu kombinasyondur:

- resmi veri zinciri kurmak
- zaman uyumlu panel üretmek
- yorumlanabilir istatistiksel sonuç vermek
- gerçek operasyonel sıralama üretmek

## 13. Mevcut sınırlılıklar

- prototip canlı AWS hesapta henüz doğrulanmadı
- GLMM tüm panel yerine full date-based splitlerden alınan stratified sample üzerinde fit edildi
- canlı AWS deploy gerçek hesapta henüz bitmedi
- metrikler dürüst ama çok yüksek değil; problem doğası gereği zor

## 14. Sonraki en doğru adımlar

1. gerçek AWS deploy'u tamamlamak
2. final anlatıda benchmark mı yoksa inference stack mi öne çıkacağını netleştirmek
