# NYC Heating Complaint Risk
## Kısa Bilgilendirme Kağıdı

## Bu broşürü nasıl oku?

Sunumu dinlerken şu 3 soruya bak:

1. Problem gerçek ve önemli mi?
2. Veri gerçekten resmi ve savunulabilir mi?
3. Çıktı sahada uygulanabilir mi?

## Bu proje ne yapıyor?

New York'ta hangi binaların ertesi gün `heating / hot water` şikayeti üretme riskinin yüksek olduğunu tahmin ediyor ve bir `inspection priority list` üretiyor.

Ana karar sorusu:

`Yarın önce hangi binalara gidilmeli?`

## Bu proje ne yapmıyor?

- yaz sıcak dalgası modeli değil
- sadece geçmişi raporlayan dashboard değil
- tam production AWS deploy henüz tamamlanmadı

## Hangi veriler kullanılıyor?

- NYC 311
- HPD complaints
- HPD buildings
- HPD registrations
- HPD violations
- Heat Sensor Program
- NOAA günlük hava verisi
- Census CRE vulnerability

Tamamı resmi açık veri.

## Analiz birimi ne?

- `building-day`

Yani her bina için her gün bir satır düşünülüyor.

## Hangi yöntemler kullanıldı?

- kural tabanlı baseline
- calibrated logistic benchmark
- `GEE logistic`
- `GLMM diagnostic`
- `Negative Binomial`
- seasonal `ANOVA`

## Dinlerken en önemli 4 sayı

- `282,296` complaint
- `36,170` bina
- `8,789,310` dense building-day satırı
- `2024-10-01 -> 2025-05-31` heat-season penceresi

## Sonuçları nasıl okumalıyım?

- bu problemde `F1` tek başarı ölçüsü değil
- çünkü prevalence düşük
- bu yüzden `ranking` gücü çok önemli

En kritik operasyonel sonuç:

- `Mean Precision@50 = 0.2743`
- `Mean Lift@50 = 47.3438`

Bu şu anlama gelir:

`Modelin her gün önerdiği ilk 50 bina, rastgele seçimden çok daha güçlü bir denetim sinyali taşıyor.`

## En önemli bulgular

- soğuk günler complaint yükünü artırıyor
- geçmiş complaint yoğunluğu güçlü sinyal taşıyor
- `CRE vulnerability` ana çıkarım modeli olan GEE tarafında pozitif sinyal taşıyor
- mevsim etkisi `ANOVA` ile güçlü biçimde doğrulanıyor

## Çıktı ne?

- calibrated risk skoru
- complaint count tahmini
- ranked inspection priority list
- yorumlanabilir katsayılar ve istatistiksel çıkarım

## Dürüst sınırlılıklar

- GLMM building-panel stratified sample üzerinde diagnostic olarak çalıştırıldı; ana kanıt değildir
- canlı AWS deploy henüz tamamlanmadı

## En kısa özet

`Bu çalışma, resmi verilerle hangi binaların ertesi gün heating/hot water complaint üretme riski taşıdığını tahmin eden ve bunu denetim önceliğine çeviren bir kamu analitiği prototipidir.`
