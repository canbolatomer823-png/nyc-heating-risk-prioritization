# NYC Heating Risk - Tahta, Brosur ve Sunum Kontrol Paketi

**Ogrenci:** Omer Canbolat
**Numara:** 22050622
**Ders:** IST-312 Istatistik Hesaplama
**Kullanim amaci:** Sinifta tahtaya yazilacaklar, sunum sirasinda soylenilecek kisa cumleler, brosur anlatimi ve demo kaniti.

---

## 1. En net proje cumlesi

Tahtaya veya sunum basina yaz:

> Resmi acik verilerle, NYC'de ertesi gun heating / hot water complaint riski yuksek binalari tahmin edip denetim onceligine ceviren bir building-day karar destek prototipi gelistirdim.

Bu cumle ne demek?

- **Resmi acik veri:** NYC 311, HPD, NOAA GSOD, Census CRE.
- **Building-day:** Her satir bir bina ve bir gunu temsil eder.
- **Tahmin:** Ertesi gun complaint var mi, yok mu?
- **Denetim onceligi:** Butun binalara gidilemeyecegi icin once hangi binalara bakilmali?
- **Karar destek:** Model otomatik ceza veya otomatik denetim karari vermez; insana risk siralamasi sunar.

Kacinilacak cumle:

> Heating problemini cozdum.

Dogru cumle:

> Heating/hot water sikayet riski yuksek binalari daha erken ve kanitli onceliklendiren bir prototip gelistirdim.

---

## 2. Tahtaya yazilacak ana problem

Tahtada ilk blok:

```text
Problem:
Denetim kapasitesi sinirli.
Her binaya ayni anda gidilemez.

Karar sorusu:
Yarin hangi binalara once gidilmeli?
```

30 saniyelik aciklama:

"Bu projede asil mesele sadece tahmin yapmak degil. Tahmini kullanarak sinirli denetim kapasitesini daha dogru siralamak. Yani modelin ciktisi bir risk skoru ve inspection priority list."

---

## 3. Tahtaya cizilecek veri akisi

Tahtaya soldan saga ciz:

```text
NYC 311 complaints
        +
HPD buildings / registrations / violations
        +
NOAA daily weather
        +
Census CRE vulnerability
        |
        v
Building-day panel
        |
        v
Y(t+1): ertesi gun complaint var mi?
        |
        v
Calibrated logistic risk score
        |
        v
Top 50 inspection priority list
        |
        v
why_risky + FastAPI + Docker + AWS proof
```

Aciklama:

- 311 sikayet akisini verir.
- HPD bina gecmisi ve violation bilgisini verir.
- NOAA gunluk hava bilgisini verir.
- Census CRE bolgesel kirilganlik bilgisini verir.
- Hepsi building-day panelde birlesir.
- Hedef degisken ertesi gun complaint olup olmamasidir.

---

## 4. Tahtaya yazilacak hedef degisken

```text
Birim:
i = bina
t = gun

Y(i, t+1) = 1  -> ertesi gun heating/hot water complaint var
Y(i, t+1) = 0  -> ertesi gun complaint yok
```

Kisa aciklama:

"Model bugunun ve gecmisin bilgisine bakarak yarin icin risk skoru uretir. Bu nedenle gelecek bilgi sızıntısı olmamasi gerekir."

Leakage icin tahtaya yaz:

```text
Kural:
Feature'lar sadece t gunune kadar bilinen bilgilerden uretilir.
t+1 bilgisi modele sokulmaz.
```

---

## 5. Tahtaya yazilacak istatistik hipotezleri

### ANOVA

```text
Soru:
Aylara gore ortalama complaint yogunlugu farkli mi?

H0: mu_Oct = mu_Nov = ... = mu_May
H1: En az bir ayin ortalamasi farklidir.

Sonuc:
F = 33.62
p < 0.0001
eta^2 ~= 0.500
```

Sozlu yorum:

"ANOVA burada tahmin modeli degil. Modelleme oncesi mevsimsel farki test etmek icin kullanildi. Sonuc, heat-season icinde aylara gore complaint yogunlugunun anlamli sekilde degistigini gosteriyor."

### Logistic regression

```text
Soru:
Yarin complaint olur mu? 0/1

logit(P(Y=1)) =
beta0
+ beta1 * complaint_gecmisi
+ beta2 * weather
+ beta3 * HPD_violation
+ beta4 * CRE_vulnerability
+ ...
```

Sozlu yorum:

"Logistic regression ana operasyonel modeldir. Cunku hedef binary. Ciktisi olasilik oldugu icin binalari risk skoruna gore siralayabildim."

### Negative Binomial

```text
Soru:
Complaint sayisi hangi faktorlerle artiyor?

Count hedef:
0, 1, 2, 3, ... complaint adedi

Neden NB?
Count veride overdispersion olabilir.
Varyans ortalamadan buyukse Poisson zayif kalir.
```

Sozlu yorum:

"Negative Binomial ana karar modeli degil. Sayim verisi tarafini kontrol etmek ve complaint sayisinin hangi sinyallerle arttigini okumak icin kullanildi."

### GEE / GLMM

```text
Soru:
Ayni binanin tekrar eden gunleri sonucu etkiler mi?

Panel veri:
Bir bina birden fazla gun gozlenir.
Gozlemler tamamen bagimsiz kabul edilemez.

GEE / GLMM:
Tekrar eden bina yapisini diagnostic olarak kontrol eder.
```

Sozlu yorum:

"Primary model logistic ranking. GEE ve GLMM destekleyici istatistiksel kontrol ve diagnostic katmanidir."

---

## 6. Yontemleri bir tabloda anlat

Tahtaya veya sozlu anlatima uygun tablo:

| Yontem | Ne sordum? | Neden kullandim? | Cikti |
|---|---|---|---|
| Logistic regression | Yarin complaint olur mu? | Hedef 0/1 oldugu icin | Risk olasiligi ve priority rank |
| ANOVA | Aylar arasinda ortalama fark var mi? | Mevsimsel farki test etmek icin | F=33.62, p<0.0001, eta²≈0.500 |
| Negative Binomial | Complaint sayisi nasil degisiyor? | Count veri ve overdispersion icin | Count-side destek model |
| GEE | Ayni bina tekrarlarini nasil yorumlarim? | Clustered panel yapi icin | Yorumlanabilir risk sinyalleri |
| GLMM | Bina random effect fikri tutarli mi? | Mixed-effects diagnostic icin | Destekleyici kontrol |
| Calibration / Backtest | Skorlar zamanla dayanikli mi? | Tek split yetmesin diye | OOT ve ranking kaniti |

Hoca sorarsa kisa cevap:

"Tek bir yontemle her seyi cozmeye calismadim. Logistic regression tahmin ve siralama icin, ANOVA mevsimsel fark icin, Negative Binomial count verisi icin, GEE/GLMM tekrar eden bina yapisini kontrol icin kullanildi."

---

## 7. Sunumda mutlaka gosterilecek sayilar

| Sayi | Ne anlatiyor? | Nasil yorumlanir? |
|---:|---|---|
| 282,296 | Heating / hot water complaint kaydi | Veri gercek ve buyuk |
| 36,170 | Benzersiz bina | Problem bina duzeyinde |
| 8.7M | Building-day panel satiri | Model gunluk panel uzerinde kuruldu |
| AUC 0.8036 | Ayrim gucu | Model pozitif/negatif ayriminda anlamli sinyal yakaliyor |
| P@50 0.2743 | Ilk 50 listedeki basari | Denetim kapasitesi 50 bina ise en onemli metriklerden biri |
| Lift@50 47.3x | Rastgeleye gore kazanc | Top list rastgele siralamadan cok daha yogun pozitif yakaliyor |
| ANOVA F=33.62 | Mevsimsel fark testi | Aylar arasinda anlamli fark var |
| OOT P@50 0.689 | Zaman disi test | Sonraki pencere ranking performansi ayrica kontrol edildi |

Kisa yorum:

"Bu sayilarin hepsi ayni seyi kanitlamiyor. Bazilari veri buyuklugunu, bazilari istatistiksel farki, bazilari da operasyonel siralama kalitesini gosteriyor."

---

## 8. Brosur nasil tanitilacak?

QR slaytinda soylenecek kisa metin:

"Kagit dagitmak yerine QR kod koydum. Bu PDF brosurde projenin problemi, veri kaynaklari, yontemleri, model bulgulari ve sinirlari tek yerde var. Ozellikle yontem sayfasinda logistic regression, ANOVA, Negative Binomial ve GEE/GLMM'i hangi amacla kullandigimi lisans seviyesinde ozetledim."

Brosurde sinif arkadaslarinin bakmasi gereken yerler:

| Brosur bolumu | Ne anlatir? |
|---|---|
| Ilk sayfa | Problem, veri buyuklugu, resmi kaynaklar, heat-season profil |
| Yontem sayfasi | Regresyon, ANOVA, NB, GEE/GLMM ne icin kullanildi |
| Operasyonel cikti | Priority list, top riskli binalar, why_risky |
| SSS / Guvenilirlik | Hoca sorularina kisa cevaplar, CI/OOT/Docker/AWS proof |

Uyari:

```text
QR brosur PDF'ini acar.
QR local API dashboard'u acmaz.
127.0.0.1 sadece benim laptopumdur.
```

---

## 9. Demo kaniti nasil gosterilecek?

Derste zaman varsa terminalde:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk class-demo-check
```

Beklenen:

```text
Overall: READY
```

Sonra:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof
```

Rapor:

```bash
cat /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/demo_proof.md
```

Tarayici dashboard:

```text
http://127.0.0.1:8000/dashboard?top_n=10
```

Demo sirasinda soylenecek metin:

"Bu komut model artifact'lerini yukleyip lokal FastAPI endpointlerini test ediyor. Health, metadata, priorities, record lookup ve score endpointlerinin yanitlari dosyaya yaziliyor. Bu nedenle proje sadece slayt degil, ayni artifact'lerden tekrar calisan bir prototip."

Eger dashboard acilmazsa:

"Local server su anda kapali olabilir; bu durumda demo proof raporu endpointlerin daha once ayni artifact'lerle basariyla test edildigini gosteriyor."

---

## 10. AWS ve maliyet sorusu gelirse

Kisa cevap:

"AWS tarafinda ECR, S3 ve EKS zinciri icin live proof alindi; sonra maliyet dogmamasi icin kaynaklar kapatildi. Bu nedenle su an surekli acik bir public endpoint iddiasi yapmiyorum. Sinifta local API ve timestamped AWS proof dosyalarini gosteriyorum."

Tahtaya gerekirse yaz:

```text
Local proof:
FastAPI + Docker + demo-proof

Cloud proof:
S3 artifact + ECR image + EKS LoadBalancer
Timestamped live proof alindi, sonra kapatildi.
```

Yanlis cumle:

> AWS endpoint su an canli.

Dogru cumle:

> AWS canli kaniti alindi; maliyet icin kapatildi.

---

## 11. En sik hoca sorulari

| Soru | Kisa cevap |
|---|---|
| Bu proje hangi soruna care oluyor? | Sinirli denetim kapasitesinde once hangi binalara bakilmasi gerektigini siraliyor. |
| Neden heat wave degil? | Bu proje heating season complaint modelidir; yaz heat-wave modeli degildir. |
| Ana model hangisi? | Calibrated logistic ranking. |
| GLMM ana model mi? | Hayir, diagnostic. Ana karar listesi logistic ranking ile uretiliyor. |
| ANOVA ne ise yaradi? | Aylara gore complaint ortalamasinda anlamli fark var mi test etti. |
| NB neden var? | Complaint sayisi count veri oldugu ve overdispersion riski tasidigi icin. |
| F1 dusukse sorun mu? | Pozitif sinif nadir. Bu nedenle ranking metrikleri, P@50 ve Lift@50 daha operasyonel. |
| Equity iddiasi nedir? | CRE vulnerability katmani risk okuma ve equity-weighted ranking icin eklendi; otomatik karar degil. |
| Production-ready mi? | Hayir, production'a tasinabilir audit-ready prototip. |
| Supabase nerede? | Ana kapsamdan cikarildi; opsiyonel SQL appendix olarak duruyor. |

---

## 12. Son 30 saniye kapanis

"Bu projede resmi acik verileri building-day panelde birlestirdim, leakage audit ile veri sizintisini kontrol ettim, logistic regression ile ertesi gun complaint riskini siraladim, ANOVA ve diger istatistiksel modellerle bulgulari destekledim. Cikti olarak denetim ekipleri icin priority list ve why_risky aciklamasi urettim. FastAPI, Docker ve AWS proof ile proje notebook seviyesinde kalmadi; servislenebilir bir karar destek prototipine donustu."

---

## 13. Son kontrol listesi

Sunumdan once isaretle:

- [ ] Ana sunum PDF aciliyor.
- [ ] PPTX aciliyor.
- [ ] QR slayti kapaktan sonra geliyor.
- [ ] QR telefonda brosur PDF'ini aciyor.
- [ ] Brosur yontem sayfasi okunabilir.
- [ ] `class-demo-check` sonucu `READY`.
- [ ] `demo-proof` calisiyor.
- [ ] Docker Desktop acik.
- [ ] Dashboard gerekiyorsa `127.0.0.1:8000` acik.
- [ ] E-kampus zip 200 MB altinda.
- [ ] AWS proof ve shutdown proof pakette.
- [ ] Supabase ana iddia olarak anlatilmiyor.
- [ ] "Production-ready" yerine "production'a tasinabilir prototip" deniyor.
