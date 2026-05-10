# NYC Heating Complaint Risk - 30 Dakikalık Sınıf Anlatımı

Bu akış, final heat-season build ile tamamen hizalıdır.

## 1. Açılış cümlesi

`New York'ta hangi binaların ertesi gün heating veya hot water complaint üretme riskinin yüksek olduğunu resmi açık verilerle tahmin eden ve bunu denetim önceliğine çeviren bir building-day karar destek prototipi geliştirdim.`

## 2. İlk 5 rakam

Tahtaya bunları yaz:

- `282,296` complaint kaydı
- `36,170` benzersiz bina
- `8,789,310` dense building-day satırı
- `2024-10-01 -> 2025-05-31` heat-season penceresi
- `Precision@50 = 0.2743`

## 3. 30 dakikalık akış

### Dakika 0-4 | Problem

- şehir bütün binalara aynı anda müdahale edemez
- karar sorusu: `yarın önce hangi binalara gidilmeli?`
- kapsam: `summer heatwave` değil, `heating/hot water complaint risk`

### Dakika 4-8 | Başarı kriteri

- başarıyı sadece `F1` ile ölçmediğini söyle
- düşük base-rate ortamında doğru sıralama üretmenin daha kritik olduğunu vurgula
- şu iki rakamı söyle:
  - `Mean Precision@50 = 0.2743`
  - `Mean Lift@50 = 47.3438`

### Dakika 8-13 | Veri ve karar birimi

- veri kaynakları: `311 + HPD + NOAA + Census CRE`
- sentetik veri yok
- analiz birimi: `building-day`
- neden `building-day`:
  - hava günlük değişir
  - müdahale bina bazında yapılır

### Dakika 13-16 | Veri akışı

- complaint -> building -> registration -> violations -> weather -> CRE
- complaint tarihine kadar olan violation snapshot mantığını anlat
- şu cümleyi net kullan:
  - `future leakage riskini kapattım ve panel audit ile doğruladım`

### Dakika 16-19 | Kalite kontrol

- `duplicate row = 0`
- `future as-of row = 0`
- `label mismatch = 0`
- `weather missing = 0`
- şunu net söyle:
  - `Bu audit olmadan proje sahte performans üretebilirdi.`

### Dakika 19-22 | Validation ve calibration

- `5 fold` expanding monthly backtest mantığını anlat
- calibration yöntemi: `Platt`
- threshold yaklaşımı: `tuned threshold`
- şu iki rakamı söyle:
  - `Mean Precision@10 = 0.4531`
  - `Mean Precision@50 = 0.2743`

### Dakika 22-25 | Modeller

- `baseline`
- `calibrated logistic benchmark`
- `GEE logistic`
- `GLMM diagnostic`
- `Negative Binomial`

Şu iki cümleyi özellikle kur:

- `Ana çıkarım kanıtını GEE ile, count hedefini Negative Binomial ile kurdum.`
- `GLMM tarafını building-panel diagnostic olarak çalıştırdım; convergence sınırlılığı olduğu için ana başarı kanıtı yapmadım.`

### Dakika 25-28 | Sonuçlar

- Logistic test F1: `0.1641`
- GEE test F1: `0.1914`
- GLMM test F1: `0.1384`
- NB test MAE: `0.0616`
- Monthly ANOVA: `F=33.6227`, `p<0.0001`

Yorum:

- problem zor
- base rate çok düşük
- bu yüzden operasyonel ranking ve yorumlanabilirlik ana değer

### Dakika 28-30 | Operasyonel çıktı ve dürüst kapanış

- inspection priority list'i göster
- `bu sadece skor değil, müdahale sırası` cümlesini kur
- sınırlılıkları dürüstçe söyle
- sonraki aşama olarak canlı AWS deploy'u belirt

## 4. Slide Sırası

1. problem ve proje cümlesi
2. karar problemi ve başarı kriteri
3. veri kaynakları + building-day mimarisi
4. leakage audit ve veri kalite kontrolü
5. heat-season ve mevsimsel profil
6. validation, calibration ve ranking mantığı
7. model ailesi
8. etkiler, ANOVA ve equity bulgusu
9. priority list
10. sınırlılık + sonraki adım + kapanış

## 5. Tahtaya yazılacak çekirdek ifadeler

`Risk_it = f(weather_it, complaint_history_it, violations_it, building_i, vulnerability_i)`

`Y1 = next_day_positive_flag`

`Y2 = next_day_complaint_count`

`Calibrated logistic + GEE logistic + Binomial GLMM diagnostic + Negative Binomial`

`Success != only F1`

`Operational value = ranking + interpretability`

## 6. Hazır cevaplar

### Neden bu proje önemli?

- çünkü denetim ekipleri tüm binalara aynı anda gidemez
- bu sistem ertesi gün için öncelik sinyali üretir

### Neden building-day?

- hava günlük değişir
- müdahale bina bazında yapılır
- bu yüzden en doğal analiz birimi building-day'dir

### Neden calibrated logistic?

- benchmark olarak güçlü ve tekrar üretilebilir
- ranking kalitesini net ölçmemi sağlıyor
- düşük prevalence ortamında raw probability yerine calibration önemli

### Neden GEE?

- aynı bina tekrar tekrar gözleniyor
- satırlar bağımsız değil
- GEE bina içi bağımlılığı daha dürüst ele alıyor

### Neden GLMM?

- random intercept ile bina bazlı heterojenliği açıkça modelliyor
- mixed-effects sorusuna teknik olarak doğru cevap veriyor
- ama tüm panelde doğrudan değil, full date-based splitlerden alınan stratified sample üzerinde fit edildi

### Neden Negative Binomial?

- complaint sayısı count data
- aşırı saçılım var
- bu yüzden Poisson yerine Negative Binomial daha uygun

### Neden F1 çok yüksek değil?

- çünkü veri gerçek dünya verisi
- hedef zor ve prevalence düşük
- proje değeri sadece sınıflandırma skorunda değil, önceliklendirme gücünde

### Equity yaptın mı?

- evet, tract-level `CRE` vulnerability katmanı dense panele ve son modellere entegre edildi
- GEE tarafında vulnerability terimi pozitif kaldı; GLMM diagnostic olarak tutuldu

### Bu proje neden klişe değil?

- sadece dashboard veya geçmiş raporu değil
- resmi veri entegrasyonu + leakage audit + istatistiksel çıkarım + operasyonel priority list aynı yapıda birleşiyor

## 7. Dürüst sınırlılık cümlesi

`Mevcut sürüm heat-season penceresine genişletildi, equity katmanı entegre edildi ve GLMM mixed-effects kontrolü diagnostic olarak eklendi. Dürüst kalan sınırlılık, GLMM'in full panel yerine stratified sample üzerinde fit edilmesi, convergence sınırlılığı nedeniyle ana kanıt olmaması ve canlı AWS deploy'un henüz gerçek hesapta tamamlanmamış olmasıdır.`

## 8. Kapanış cümlesi

`Bu çalışma geçmişi raporlayan bir dashboard değil; resmi açık verilerle ertesi gün complaint riski üreten ve bunu saha önceliğine çeviren bir kamu analitiği prototipi.`
