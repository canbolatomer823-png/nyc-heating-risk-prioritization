# NYC Heating Complaint Risk
## İstatistik Anlatım Kılavuzu

Bu dosya, sunum sırasında veya soru-cevapta projenin istatistik yönünü güçlü anlatabilmen için hazırlandı.

Ana fikir:

`Bu projede istatistiği sadece tahmin üretmek için değil, ilişkiyi yorumlamak, model seçimini gerekçelendirmek ve mevsimsel farkı test etmek için kullandım.`

---

## 1. Bu projede istatistik neden gerekliydi?

Sunumda bunu şöyle söyle:

`Ben sadece yarın hangi bina riskli diye skor üretmek istemedim. Aynı zamanda hangi değişkenlerin riski artırdığını, bunu nasıl savunabileceğimi ve mevsimsel yapının gerçekten anlamlı olup olmadığını da göstermek istedim.`

Kısa versiyon:
- `tahmin` için model
- `yorum` için regresyon katsayısı
- `bağımlı tekrar gözlemler` için clustered inference ve diagnostic mixed-effects kontrolü
- `mevsim farkı` için ANOVA
- `count hedef` için Negative Binomial

---

## 2. Bağımlı değişkenleri nasıl tanımladım?

Projede aslında iki ayrı hedef var:

### Hedef 1 | Binary risk

`Ertesi gün bu binada complaint olacak mı olmayacak mı?`

Bunu şöyle tanımlıyorsun:

`Y1 = next_day_positive_flag`

Bu hedef için:
- `calibrated logistic regression`
- `GEE logistic`
- `Binomial GLMM`

kullandın.

### Hedef 2 | Count risk

`Ertesi gün bu binada kaç complaint bekleniyor?`

Bunu şöyle tanımlıyorsun:

`Y2 = next_day_complaint_count`

Bu hedef için:
- `Negative Binomial`

kullandın.

Sunum cümlesi:

`Yani ben problemi sadece var/yok şeklinde değil, aynı zamanda şikayet hacmi açısından da modelledim.`

---

## 3. Regresyonu neden kullandım?

Bu soruya en net cevap:

`Regresyonu, risk ile açıklayıcı değişkenler arasındaki yönü ve büyüklüğü yorumlayabilmek için kullandım.`

### Logistic regression neden?

Çünkü ilk hedef binary:
- complaint var / yok

Logistic regression burada:
- olasılık üretir
- benchmark kurar
- tekrar üretilebilir
- calibration ile operasyonel hale gelir

Sunumda söyle:

`Calibrated logistic regression benim benchmark modelim. Çünkü hem olasılık veriyor hem de ranking kalitesini net ölçmeme izin veriyor.`

---

## 4. Neden sadece tek logistic regression değil?

Çünkü veride aynı bina tekrar tekrar gözleniyor.

Bu ne demek?
- satırlar bağımsız değil
- aynı binanın geçmişi geleceğini etkiliyor
- klasik bağımsız gözlem varsayımı zayıflıyor

Bu yüzden iki ileri yapı kullandın:

### GEE logistic

Neden?
- `clustered / repeated observations` için
- aynı bina içindeki korelasyonu daha dürüst ele almak için
- marginal yani popülasyon düzeyinde ilişki yorumu almak için

Sunum cümlesi:

`GEE kullanmamın nedeni, aynı binayı tekrar tekrar gözlemliyor olmam. Bu yüzden bağımsız satır varsayımı yerine clustered inference kurdum.`

### Binomial GLMM diagnostic

Neden?
- `random intercept` ile bina bazlı heterojenliği açık modellemek için
- mixed-effects yapısını diagnostic olarak kontrol etmek için

Sunum cümlesi:

`GLMM ile building_id random intercept diagnostic denemesi kurdum. Ancak VB optimizer tam converge etmediği için bunu ana başarı kanıtı olarak kullanmadım.`

Dürüstlük cümlesi:

`GLMM building-panel stratified sample üzerinde çalıştırıldı; ana çıkarım kanıtını GEE, ana operasyonel kanıtı calibrated logistic ranking taşıyor.`

---

## 5. Negative Binomial neden kullandım?

Çünkü complaint sayısı:
- `count data`
- sıfır yoğun
- aşırı saçılım taşıyor

Poisson neden yetmiyor?
- Poisson ortalama ile varyansı eşit varsayar
- gerçek complaint verisinde bu çoğu zaman bozulur

Bu yüzden:
- `Negative Binomial` daha uygun

Sunum cümlesi:

`Count hedef için Poisson yerine Negative Binomial kullandım çünkü complaint verisi aşırı saçılım içeriyor.`

Projedeki rolü:
- binary riskten ayrı olarak
- `şikayet hacmini` modellemek

Bu çok iyi bir savunma cümlesi:

`Yani sadece complaint olur mu diye değil, ne kadar complaint yükü oluşabilir diye de baktım.`

---

## 6. ANOVA bu projede ne işe yaradı?

En net cevap:

`ANOVA'yı tahmin üretmek için değil, heat-season boyunca complaint yükünün aylara göre anlamlı biçimde değişip değişmediğini test etmek için kullandım.`

Yani ANOVA burada:
- prediction modeli değil
- `temel istatistiksel fark testi`

Test edilen fikir:

`Aylık complaint ortalamaları aynı mı?`

ve

`Aylık positive-building ortalamaları aynı mı?`

Projede bulduğun sonuç:
- `Monthly complaints ANOVA: F = 33.6227`
- `p < 0.0001`
- `eta_sq = 0.5004`

Bu ne demek?

`Heat-season boyunca complaint yükü aylara göre sabit değil; mevsimsel fark güçlü ve anlamlı.`

Sunum cümlesi:

`ANOVA ile gösterdim ki complaint yükü aylar arasında rastgele oynamıyor; mevsimsel fark güçlü ve istatistiksel olarak anlamlı.`

Çok basit anlatım:

`Yani Ocak ile Mayıs aynı davranmıyor; hava ve sezon etkisi gerçek.`

---

## 7. İstatistiksel düşünce akışım neydi?

Bunu hocaya çok güçlü anlatabilirsin:

### Adım 1
Önce karar problemini tanımladım:

`Yarın önce hangi binalara gidilmeli?`

### Adım 2
Sonra uygun analiz birimini kurdum:

`building-day`

### Adım 3
Leakage riskini kapattım:

`geçmişten geleceği tahmin edecek temiz panel`

### Adım 4
Tahmin için benchmark kurdum:

`calibrated logistic`

### Adım 5
İlişkiyi ve bağımlılığı yorumlamak için daha istatistiksel modeller ekledim:

`GEE + GLMM + Negative Binomial`

### Adım 6
Mevsimsel farkı ayrıca test ettim:

`ANOVA`

En temiz özet:

`Yani metodolojim önce prediction, sonra inference, sonra hypothesis testing mantığıyla ilerledi.`

---

## 8. Regresyon katsayılarını nasıl anlatmalıyım?

Kural:

`Effect > 1` ise risk artıyor  
`Effect < 1` ise risk azalıyor

Projede öne çıkan örnekler:

- `GEE CRE vulnerability OR = 2.5815`
- `GLMM diagnostic: convergence sınırlılığı var, ana kanıt değil`
- `weather_temp_drop_c` pozitif
- `recent_complaint_flag` pozitif

Sunum cümlesi:

`Bu katsayılar bana şu yorumu yapma hakkı veriyor: vulnerability, hava şoku ve yakın geçmiş complaint davranışı risk artışıyla birlikte hareket ediyor.`

---

## 9. “Neden bu kadar çok model kullandın?” sorusuna cevap

Hazır cevap:

`Çünkü her model başka bir ihtiyacı karşılıyor. Calibrated logistic operasyonel ranking veriyor, GEE clustered inference veriyor, GLMM diagnostic mixed-effects kontrolü sağlıyor, Negative Binomial count hedefi modelliyor. ANOVA da mevsimsel farkı test ediyor.`

Kısa versiyon:

`Tek model değil, problem yapısına uygun model ailesi kurdum.`

---

## 10. “F1 neden düşük?” sorusuna istatistik cevap

Hazır cevap:

`Çünkü hedef çok düşük prevalence'a sahip. Held-out actual positive rate yaklaşık yüzde 0.59. Böyle bir problemde F1'in sınırlı kalması şaşırtıcı değil. O yüzden ben başarıyı ranking kalitesi, lift, calibration ve yorumlanabilir istatistikle birlikte okudum.`

Bu çok önemli.

Çünkü seni şuradan çıkarır:
- “Model kötü mü?”

ve şuraya taşır:
- “Problem zor ama model operasyonel olarak işe yarıyor mu?”

---

## 11. “ANOVA neden ekledin?” sorusuna kısa cevap

`Çünkü yalnızca model kurmak istemedim. Heat-season boyunca complaint yükünün gerçekten aylar arasında değişip değişmediğini ayrıca test etmek istedim. Böylece mevsimsellik varsayımımı model dışında da istatistiksel olarak doğrulamış oldum.`

---

## 12. “Mixed-effects nerede?” sorusuna kısa cevap

`Mixed-effects tarafını Binomial GLMM diagnostic modeliyle kontrol ettim. building_id için random intercept kullandım. Model stratified building-panel sample üzerinde fit edildi; VB optimizer tam converge etmediği için ana başarı kanıtı yapmıyorum.`

Bu cümleyi aynen kullanabilirsin.

---

## 13. Sınıfta kullanabileceğin çok güçlü 6 cümle

1. `Bu projede istatistiği sadece tahmin için değil, ilişkiyi yorumlamak için de kullandım.`
2. `Binary hedef için logistic ailesi, count hedef için Negative Binomial kullandım.`
3. `Aynı bina tekrar tekrar gözlendiği için clustered inference ve diagnostic mixed-effects kontrolü kurmam gerekti.`
4. `GEE bana ana marginal inference, GLMM bana random-intercept diagnostic kontrol verdi.`
5. `ANOVA ile mevsimsel complaint yükünün aylar arasında anlamlı biçimde değiştiğini doğruladım.`
6. `Yani metodoloji prediction, inference ve hypothesis testing katmanlarının birlikte kurulduğu bir yapı oldu.`

---

## 14. En kısa istatistik özeti

Eğer çok kısa anlatman gerekirse şunu söyle:

`Bu projede calibrated logistic regression ile operasyonel ranking kurdum, GEE ile clustered inference yaptım, GLMM'i diagnostic mixed-effects kontrolü olarak tuttum, Negative Binomial ile complaint count'u modelledim, ANOVA ile de mevsimsel farkı test ettim.`
