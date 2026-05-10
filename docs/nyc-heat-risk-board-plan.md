# NYC Heating Complaint Risk
## Tahtaya Yazılacak Hipotezler, İstatistik Kısımlar ve Çizim Akışı

Bu dosya, sınıfta tahtaya ne yazacağını ve hangi sırayla anlatacağını hızlıca takip etmen için hazırlandı.

Ana mantık:

`Problem -> Veri -> Hipotez -> Model -> Test -> Operasyonel çıktı`

---

## 1. Tahtaya en başta yaz

Tahtanın üst kısmına şu 5 ifadeyi yaz:

`building-day`

`next-day risk`

`311 + HPD + NOAA + CRE`

`ranking + interpretability`

`inspection priority list`

Bunlar sunum boyunca ana omurgan olsun.

---

## 2. Problem cümlesi

Tahtaya kısa problem cümlesi:

`Sınırlı denetim kapasitesi varken yarın önce hangi binalara gidilmeli?`

Altına bir satır daha:

`Amaç: heating / hot water complaint riskini önceliklendirmek`

Söylemen gereken:

`Ben bu projede arızayı tamir eden bir sistem kurmadım; hangi binalara önce gidilmesi gerektiğini daha akıllı seçen bir karar destek sistemi kurdum.`

---

## 3. Analiz birimi

Tahtaya yaz:

`Analiz birimi = building-day`

Altına:

`1 bina x 1 gün = 1 gözlem`

Söyle:

`Bunu seçtim çünkü hava günlük değişiyor ama müdahale bina bazında yapılıyor.`

---

## 4. Veri akışını tahtaya çiz

Soldan sağa kutular çiz:

`311 complaints -> HPD building history -> NOAA weather -> Census CRE -> building-day panel`

Kutuların altına küçük notlar:

- `311 = şikayet`
- `HPD = bina / violation / registration`
- `NOAA = sıcaklık / yağış / heating degree`
- `CRE = vulnerability`

Son kutunun altına:

`Output: next-day risk + next-day count`

Söyle:

`Ham resmi kayıtları tek karar biriminde birleştirdim ve building-day panel oluşturdum.`

---

## 5. Bağımlı değişkenler

Tahtaya tam olarak şunu yaz:

`Y1 = next_day_positive_flag`

`Y2 = next_day_complaint_count`

Altına şunu ekle:

`Y1 -> binary risk`

`Y2 -> count risk`

Söyle:

`Ben problemi sadece olur/olmaz diye değil, aynı zamanda ertesi gün kaç complaint beklenir diye de modelledim.`

---

## 6. Regresyon mantığı

Tahtaya şu genel formülü yaz:

`Risk_it = f(weather_it, history_it, violations_it, building_i, vulnerability_i)`

Bir satır daha:

`logit(P(Y1=1)) = beta0 + betaX + u_building`

Ve count için:

`log(E[Y2]) = beta0 + betaX`

Söyle:

`Regresyonu risk ile açıklayıcı değişkenler arasındaki yönü ve büyüklüğü yorumlayabilmek için kullandım.`

---

## 7. Hipotezler

### Ana araştırma hipotezi

Tahtaya yaz:

`H1: Weather + complaint history + violations + vulnerability -> next-day risk artışı`

Söyle:

`Ana hipotezim, hava şoku, geçmiş complaint yoğunluğu, violation geçmişi ve kırılganlığın birlikte ertesi gün complaint riskini artırdığıydı.`

### GEE / GLMM tarafı için yorum hipotezi

Tahtaya yaz:

`H2: CRE vulnerability katsayısı > 0`

`H3: recent complaint history katsayısı > 0`

`H4: weather shock katsayısı > 0`

Söyle:

`Yani vulnerability, yakın geçmiş complaint davranışı ve hava şokunun pozitif yönlü ilişki vermesini bekledim.`

### ANOVA hipotezi

Tahtaya yaz:

`H0: Aylık complaint ortalamaları eşit`

`H1: En az bir ay farklı`

İstersen ikinci satır:

`H0: Aylık positive-building ortalamaları eşit`

`H1: En az bir ay farklı`

Söyle:

`ANOVA'yı tahmin için değil, heat-season boyunca complaint yükünün aylara göre gerçekten değişip değişmediğini test etmek için kullandım.`

---

## 8. Neden bu modeller?

Tahtaya dört kutu çiz:

`Calibrated Logistic`

`GEE Logistic`

`Binomial GLMM`

`Negative Binomial`

Her kutunun altına kısa amaç yaz:

`Calibrated Logistic -> benchmark + ranking`

`GEE -> clustered inference`

`GLMM -> random intercept diagnostic`

`NB -> count data`

Söyle:

`Tek model seçmedim çünkü her model başka bir ihtiyacı karşılıyor.`

---

## 9. GEE’yi nasıl anlatacaksın?

Tahtaya yaz:

`Same building observed repeatedly`

`=> rows not independent`

`=> clustered inference needed`

Söyle:

`GEE kullanmamın nedeni aynı binayı tekrar tekrar gözlemlemem. Bu yüzden bağımsız satır varsayımı zayıf. GEE bana bina içi korelasyonu dikkate alan marginal inference verdi.`

---

## 10. GLMM’i nasıl anlatacaksın?

Tahtaya yaz:

`u_building ~ N(0, sigma^2)`

`Random intercept by building`

Söyle:

`GLMM ile building_id random intercept diagnostic denemesi kurdum; convergence sınırlılığı nedeniyle ana kanıt olarak GEE ve logistic ranking'i kullandım.`

Dürüst not:

`GLMM building-panel stratified sample üzerinde diagnostic olarak fit edildi.`

---

## 11. Negative Binomial’i nasıl anlatacaksın?

Tahtaya yaz:

`Count data`

`Overdispersion`

`Poisson yetmez -> Negative Binomial`

Söyle:

`Complaint sayısı count data olduğu ve aşırı saçılım içerdiği için count hedefte Poisson yerine Negative Binomial kullandım.`

---

## 12. ANOVA’yı nasıl anlatacaksın?

Tahtaya yaz:

`ANOVA: month -> complaint load`

`F = 33.62`

`p < 0.0001`

Söyle:

`Bu sonuç şunu söylüyor: complaint yükü aylar arasında sabit değil, mevsimsel fark güçlü ve istatistiksel olarak anlamlı.`

Kısa cümle:

`Yani Ocak ile Mayıs aynı davranmıyor.`

---

## 13. Regression coefficient yorum kuralı

Tahtaya yaz:

`Effect > 1 => risk artışı`

`Effect < 1 => risk azalışı`

Altına örnekler:

`GEE CRE OR = 2.5815`

`GLMM diagnostic, ana CRE kanıtı değil`

Söyle:

`Bu katsayılar vulnerability ve bazı weather/history terimlerinin risk artışıyla birlikte hareket ettiğini gösteriyor.`

---

## 14. Validation ve calibration kısmı

Tahtaya yaz:

`5-fold expanding backtest`

`Platt calibration`

`Precision@K`

`Lift@K`

Altına:

`Mean P@50 = 0.2743`

`Lift@50 = 47.34x`

Söyle:

`Base rate çok düşük olduğu için başarıyı sadece F1 ile okumadım; ranking kalitesi ve calibration tarafını ayrıca değerlendirdim.`

---

## 15. Leakage kısmı

Tahtaya yaz:

`future as-of = 0`

`target mismatch = 0`

`weather missing = 0`

Söyle:

`Bu audit olmadan model sahte biçimde iyi görünebilirdi. Bu yüzden leakage kontrolü projede metodolojik olarak kritik bir adımdı.`

---

## 16. En sonda tahtaya yazılacak özet

Sunumun sonuna doğru tahtaya bunu toparlayarak yaz:

`Prediction + Inference + Hypothesis Testing`

Altına:

`Logistic -> ranking`

`GEE / GLMM -> interpretation`

`NB -> count`

`ANOVA -> seasonality`

En kısa kapanış:

`Bu proje geçmişi raporlayan bir dashboard değil; ertesi gün hangi binaların önce denetlenmesi gerektiğini söyleyen kamu analitiği prototipi.`
