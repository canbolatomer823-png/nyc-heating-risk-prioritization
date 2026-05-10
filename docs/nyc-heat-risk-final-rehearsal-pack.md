# NYC Heating Risk Final Sunum Prova Paketi

**Ogrenci:** Omer Canbolat
**Numara:** 22050622
**Ders:** IST-312 Istatistik Hesaplama
**Proje:** NYC Heating / Hot Water Complaint Risk Prioritization
**Sunum suresi:** 30 dakika
**Ana dosyalar:** final sunum PDF/PPTX, QR brosur PDF, demo proof raporlari, final audit raporu

---

## 1. Sunumun ana vaadi

Bu sunumda tek bir seyi kanitlayacaksin:

> Resmi acik verilerle, ertesi gun heating / hot water complaint riski yuksek olan binalari siralayan, neden riskli olduklarini aciklayan ve bunu denetim onceligine ceviren calisan bir karar destek prototipi gelistirdim.

Bu cumle guclu ama dogru sinirdadir. Sunumda **"sikayetleri tamamen cozdum"** demiyorsun. Dedigin sey su:

> Denetim kapasitesi sinirliyken hangi binalara once bakilmasi gerektigini daha kanitli, olculebilir ve tekrar uretilebilir hale getirdim.

Bu projenin gercek hayattaki anlami:

- NYC gibi buyuk bir sehirde her binaya ayni anda gidilemez.
- Heating / hot water sikayetleri kis doneminde artar ve kiracilar icin ciddi yasam kalitesi problemidir.
- Belediye veya denetim ekibi rastgele degil, risk siralamasina gore hareket ederse sinirli kaynak daha verimli kullanilir.
- Model sadece skor vermez; `why_risky` ciktisiyle binanin neden yuksek riskli oldugunu da aciklar.
- Proje notebook seviyesinde kalmaz; FastAPI, Docker ve AWS proof ile servislenebilir prototip seviyesine tasinir.

---

## 2. Sunumdan once dosya ve komut hazirligi

Dersten once laptopta su dosyalar acilabilir durumda olsun:

| Amac | Dosya |
|---|---|
| Ana sunum PDF | `/Users/omer/Downloads/NYC_Heating_Risk_Final_Sunum_QR_Omer_Canbolat.pdf` |
| Ana sunum PPTX | `/Users/omer/Downloads/NYC_Heating_Risk_Final_Sunum_QR_Omer_Canbolat.pptx` |
| QR brosur PDF | `/Users/omer/Downloads/NYC_Heating_Risk_Brosur_Omer_Canbolat.pdf` |
| Tahta + prova PDF | `/Users/omer/Downloads/NYC_Heating_Risk_Tahta_Prova_Paketi_Omer_Canbolat.pdf` |
| E-kampus teslim paketi | `/Users/omer/Downloads/NYC_Heating_Risk_Ekampus_Teslim_Omer_Canbolat_22050622.zip` |
| Demo proof raporu | `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/demo_proof.md` |
| Final audit raporu | `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/final_project_audit.md` |
| Class demo check | `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/class_demo_check.md` |

Derste dosyalari hangi sirayla kullanacaksin:

1. `NYC_Heating_Risk_Final_Sunum_QR_Omer_Canbolat.pdf`: sinifa yansitilacak ana dosya.
2. QR slayti: sinif arkadaslari brosuru telefondan acar.
3. `NYC_Heating_Risk_Tahta_Prova_Paketi_Omer_Canbolat.pdf`: senin prova ve tahta planin; sinifa yansitmak zorunda degilsin.
4. Terminal demo: hoca "calisiyor mu?" derse `class-demo-check` ve `demo-proof`.
5. `final_project_audit.md`: teknik kanit ve eksik/yanlis iddia kontrolu.

Dersten once terminalde bir kez calistir:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk class-demo-check
```

Beklenen durum:

```text
Overall: READY
```

Eger hoca "calisiyor mu?" derse gosterilecek en guclu kanit:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof
cat /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/demo_proof.md
```

Dashboard gostermek istersen:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk serve
```

Sonra tarayicida ac:

```text
http://127.0.0.1:8000/dashboard?top_n=10
```

Onemli not:

- `127.0.0.1` sadece senin laptopundaki local API'dir.
- Hoca veya sinif arkadasi kendi telefonundan bu adrese giremez.
- QR kod ise brosur PDF'ini acar; API dashboard yerine gecmez.
- AWS canli endpoint maliyet nedeniyle surekli acik tutulmuyor. Timestamped AWS live proof ve shutdown proof kanit olarak saklaniyor.

---

## 3. 30 dakikalik ideal akis

| Dakika | Bolum | Amac |
|---:|---|---|
| 0-2 | Kapak ve problem | Projenin hangi sorunu hedefledigini netlestir |
| 2-5 | Karar problemi | "Her binaya gidilemez, once hangisi?" sorusunu kur |
| 5-8 | Veri kaynaklari | Resmi veri, building-day panel ve hedef degiskeni anlat |
| 8-11 | Veri kalite ve leakage audit | Projenin guvenilir oldugunu goster |
| 11-14 | Mevsimsel profil ve ANOVA | Istatistiksel hikayeyi baslat |
| 14-18 | Logistic regression ve validation | Ana modeli, metrikleri ve ranking mantigini anlat |
| 18-21 | GEE, GLMM, Negative Binomial | Istatistiksel destek modellerinin gorevini anlat |
| 21-24 | Operasyonel cikti | Priority list ve why_risky ornegini goster |
| 24-26 | Cloud ve demo proof | API, Docker, AWS proof zincirini anlat |
| 26-28 | Demo veya rapor kaniti | `demo-proof`, `final-audit`, dashboard |
| 28-30 | Sinirlar ve kapanis | Dürüst sinirlar, sonraki adim, ana sonuc |

Sunumda zaman kaybi olmamasi icin en kritik 3 cumle:

1. "Bu proje sikayeti yok etmiyor; denetim onceligini daha kanitli hale getiriyor."
2. "Ana operasyonel model calibrated logistic ranking; diger modeller istatistiksel yorum ve kontrol amacli."
3. "Calistigini final audit, demo proof, local API, Docker ve AWS proof dosyalariyla gosteriyorum."

---

## 4. Slayt slayt konusma metni

### Slayt 1 - Kapak

**Amac:** Projenin basligini, veri dayanaklarini ve temel karar sorusunu anlatmak.

**Soyleyecegin metin:**

"Benim projem NYC'de heating ve hot water sikayeti uretme riski yuksek olan binalari tahmin eden bir karar destek prototipi. Burada amac, sikayetleri sihirli sekilde ortadan kaldirmak degil. Amac, resmi acik verilerle hangi binalarin ertesi gun daha riskli oldugunu siralamak ve denetim kapasitesi sinirliyken once hangi binalara bakilmasi gerektigini gostermek."

"Veri tarafinda NYC 311 complaint kayitlari, HPD bina ve violation bilgileri, NOAA hava verisi ve Census CRE kirilganlik katmani var. Birimim bina-gun: yani her satir bir bina ve bir gunu temsil ediyor."

**Gosterilecek sey:** 282,296 complaint, 36,170 bina, 8.7M building-day panel.

**Gecis cumlesi:** "Once neden bu problemin bir karar problemi oldugunu anlatayim."

**Sakin deme:** "Bu sistem heating problemini tamamen cozer."

---

### Slayt 2 - Karar problemi

**Amac:** Projenin cozdüğü seyin tahmin degil, tahmine dayali onceliklendirme oldugunu kurmak.

**Soyleyecegin metin:**

"Bu projedeki asil soru su: Belediye veya denetim ekibi yarin butun binalara gidemeyecekse, once hangi binalara gitmeli? Heating complaint verisinde pozitif olay orani dusuk. Bu yuzden sadece accuracy veya F1'a bakmak yeterli degil. Bizim operasyonel olarak istedigimiz sey, listenin en ustundeki binalarda gercekten daha yogun risk yakalamak."

"Bu nedenle projede basariyi F1 ile birlikte Precision@K, Lift@K, calibration ve out-of-time validation ile okudum. Yani model sadece dogru/yanlis tahmin uretmiyor; riskli binalari siralamada ise yariyor mu diye test ediliyor."

**Gosterilecek sey:** Base rate dusuk, ranking onemli, karar problemi kutusu.

**Gecis cumlesi:** "Bu karari verebilmek icin once ham kayitlari tek bir karar birimine donusturdum."

**Sakin deme:** "F1 dusukse model kotudur." Bunun yerine: "Düşük prevalence nedeniyle ranking metrikleri daha anlamli."

---

### Slayt 3 - Veri ve karar birimi

**Amac:** Veri kaynaklarini ve building-day panel mantigini aciklamak.

**Soyleyecegin metin:**

"Ham veriler farkli yerlerden geliyor. 311 bize heating/hot water complaint akisini veriyor. HPD bina gecmisi, violation ve kayit bilgilerini veriyor. NOAA hava durumunu gunluk olarak veriyor. Census CRE ise bolgesel kirilganlik bilgisini ekliyor."

"Bunlari dogrudan karistirmadim. Hepsini building-day panelde birlestirdim. Yani bir satir sunu temsil ediyor: belirli bir binanin belirli bir gundeki durum bilgisi. Hedef degiskenim de ertesi gun o binadan heating veya hot water complaint gelip gelmeyecegi."

"Bu tasarim onemli cunku hava gunluk, complaint gunluk, denetim karari da bina duzeyinde veriliyor."

**Gosterilecek sey:** 311 + HPD + NOAA + CRE -> building-day panel -> next-day label.

**Gecis cumlesi:** "Bu noktada en kritik risk veri sizintisiydi; onu ayrica denetledim."

**Sakin deme:** "Tum veriler ayni formatta geldi." Gercekte ETL ve join yapildi.

---

### Slayt 4 - Leakage audit ve kalite kontrol

**Amac:** Hoca "gelecek bilgiyi modele soktun mu?" diye sormadan cevabi vermek.

**Soyleyecegin metin:**

"Zaman serisi veya panel projelerinde en tehlikeli hata leakage'dir. Yani modelin tahmin aninda bilemeyecegi gelecek bilgiyi feature olarak kullanmasi. Bu olursa model kagit uzerinde iyi gorunur ama gercek hayatta calismaz."

"Bu projede violation snapshot'lari complaint tarihine kadar kesildi. Lag feature'lar sadece gecmis gunlerden uretildi. Dense panelde duplicate building-date satiri yok. Audit raporunda future as-of, target mismatch ve duplicate kontrolleri sifir hata verdi."

"Bu kisim sunumun teknik guvenlik bolumu. Model sonuclari kadar, bu sonuclarin temiz bir veri tasarimindan gelmesi de onemli."

**Gosterilecek sey:** `0 duplicate rows`, `0 future as-of`, `0 target mismatch`.

**Gecis cumlesi:** "Veri guvenilir olduktan sonra once mevsimsel deseni inceledim."

**Sakin deme:** "Leakage hicbir projede olmaz." Dogru cumle: "Bu projede ayrica test ettim ve raporladim."

---

### Slayt 5 - Heat-season profili ve ANOVA

**Amac:** Istatistik dersine hitap eden ilk guclu bolumu anlatmak.

**Soyleyecegin metin:**

"Burada sadece model kurmadan once verinin mevsimsel davranisini inceledim. Heat season boyunca en soguk donemde pozitif bina sayisi da artiyor. Bu bana su soruyu sordurdu: Aylara gore complaint yogunlugu istatistiksel olarak farkli mi?"

"Bunun icin ANOVA kullandim. H0 hipotezim: Aylik ortalama complaint yogunluklari arasinda fark yoktur. H1 hipotezim: En az bir ayin ortalamasi farklidir. Sonuc F=33.62 ve p<0.0001. Eta kare yaklasik 0.500 oldugu icin fark sadece istatistiksel olarak anlamli degil, etki buyuklugu de dikkate deger."

"Yani modelleme oncesinde veri bize kis aylarinda complaint riskinin sistematik sekilde yukseldigini gosteriyor."

**Gosterilecek sey:** Aylik pozitif bina profili, F=33.62, eta²=0.500.

**Gecis cumlesi:** "Bu mevsimsel bilgiye ek olarak, bina bazli tahmin modeli kurdum."

**Sakin deme:** "ANOVA sebep-sonuc kanitlar." Dogru cumle: "ANOVA gruplar arasinda ortalama farki test eder."

---

### Slayt 6 - Validation ve calibration

**Amac:** Modelin tek bir train-test split ile gecistirilmedigini anlatmak.

**Soyleyecegin metin:**

"Bu problemde pozitif sinif cok nadir. Bu yuzden accuracy iyi bir metrik degil; cunku model hic sikayet yok dese bile yuksek accuracy alabilir. Ben bu nedenle AUC, F1, Precision@50, Lift@50, calibration ve out-of-time validation kullandim."

"Threshold 0.2 olarak tutuldu ama asil operasyonel cikti top priority list. Yani pratikte denetim ekibi 'yarin ilk 50 binaya bakalim' diyorsa, Precision@50 ve Lift@50 daha dogrudan is kararina denk geliyor."

"Held-out testte AUC 0.8036, Precision@50 0.2743. Lift@50 yaklasik 47.3x. Bu su demek: model listenin tepesinde rastgele siralamaya gore cok daha yogun pozitif bina yakaliyor."

**Gosterilecek sey:** AUC, F1, P@50, Lift@50, calibration.

**Gecis cumlesi:** "Simdi hangi modelleri ne amacla kullandigimi ayirayim."

**Sakin deme:** "F1 tek basina basari metrigidir."

---

### Slayt 7 - Logistic regression, GLMM, GEE, Negative Binomial

**Amac:** Hoca hangi yontemi neden kullandigini sordugunda net cevap vermek.

**Soyleyecegin metin:**

"Ana operasyonel modelim calibrated logistic regression. Cunku hedef degisken binary: ertesi gun complaint var mi, yok mu? Logistic regression bana olasilik uretir. Bu olasilikla binalari risk skoruna gore siralayabiliyorum."

"GEE modelini clustered inference icin kullandim. Ayni binanin farkli gunleri birbirinden tamamen bagimsiz degil. GEE bu tekrar eden bina-gun yapisini daha gercekci okumak icin kullanildi."

"Negative Binomial modelini count tarafini anlamak icin kullandim. Complaint sayilari basit Poisson varsayimina gore fazla dagilim gosterebilir; yani varyans ortalamadan buyuk olabilir. Negative Binomial bu nedenle sayim verisi icin daha uygun bir kontrol modeli oldu."

"GLMM'i primary model yapmadim. Onu mixed-effects diagnostic olarak tuttum. Cunku bina seviyesinde random intercept fikri akademik olarak guclu ama tam operasyonel ranking icin daha agir ve convergence acisindan daha dikkatli yorumlanmasi gerekiyor. Bu yuzden primary model logistic ranking, GLMM ise diagnostic."

**Gosterilecek sey:** Model tablosu: Logistic primary, GEE inference, NB count, GLMM diagnostic.

**Gecis cumlesi:** "Bu modellerin ortak sonucu, risk sinyallerini yorumlanabilir hale getirdi."

**Sakin deme:** "GLMM ana modeldir." Dogru cumle: "GLMM diagnostic; primary model calibrated logistic ranking."

---

### Slayt 8 - Istatistiksel bulgular

**Amac:** Model ciktisini sadece skor degil, yorumlanabilir istatistiksel bulgu olarak sunmak.

**Soyleyecegin metin:**

"Bu slaytta modelin ne ogrendigini okuyorum. GEE tarafinda CRE vulnerability etkisi, sicaklik dususu ve yakin gecmis complaint sinyalleri one cikiyor. Bu bana sunu soyluyor: Risk sadece bugunun havasindan gelmiyor; bina gecmisi ve bolgesel kirilganlik da onemli."

"Buradaki etki carpanlari nedensellik iddiasi degil. Yani 'CRE artarsa sikayet kesin artar' demiyorum. Dedigim sey, veri icinde bu degiskenlerin complaint riskiyle anlamli ve yorumlanabilir bir iliski tasidigi."

"Bu ayrim onemli cunku proje karar destek aracidir, otomatik ceza veya otomatik denetim sistemi degildir."

**Gosterilecek sey:** GEE CRE effect, temp drop, recent complaint effect.

**Gecis cumlesi:** "Simdi bu istatistiksel skorun sahada neye donustugunu gostereyim."

**Sakin deme:** "Bu katsayilar kesin neden-sonuc iliskisidir."

---

### Slayt 9 - Operasyonel cikti: priority list ve why_risky

**Amac:** Projenin pratik sonucunu net gostermek.

**Soyleyecegin metin:**

"Modelin sinifta en somut ciktisi bu: denetim oncelik listesi. Son skor tarihinde model en riskli 50 binayi siraliyor. Her bina icin probability, equity-weighted score ve neden riskli oldugunu aciklayan why_risky metni uretiliyor."

"Ornegin bir bina icin neden riskli aciklamasi sunu soyluyor: gecmiste cok complaint var, son gunlerde complaint gecmisi var, heat sensor program flag'i var. Bu, denetim ekibinin sadece skora degil, skoru yukselten nedenlere de bakmasini sagliyor."

"Yani proje sadece tahmin modeli degil; karar vericiye okunabilir bir liste uretiyor."

**Gosterilecek sey:** Top 5 bina tablosu, why_risky ornegi.

**Gecis cumlesi:** "Bu ciktiyi notebookta birakmadim; API ve cloud-ready hale getirdim."

**Sakin deme:** "Bu liste kesin suclu binalar listesidir." Dogru cumle: "Bu liste onceliklendirme listesidir."

---

### Slayt 10 - Cloud katmani

**Amac:** Modern veri bilimi projesi zincirini anlatmak.

**Soyleyecegin metin:**

"Projenin cloud katmani su mantikla kuruldu: model artifact'leri ve rapor ciktisi versionlanabilir sekilde saklanir; FastAPI bu artifact'leri yukleyip endpoint olarak servis eder; Docker image API'yi tasinabilir hale getirir; AWS tarafinda ECR, S3 ve EKS deployment zinciri hazirlanir."

"Burada onemli nokta su: AWS endpoint'i maliyet nedeniyle surekli acik tutmuyorum. Ama live deploy proof ve shutdown proof dosyalari var. Yani cloud entegrasyonu hayali degil; timestamped kanitla denenmis ve sonra kaynaklar kapatilmis."

"Sinifta guncel olarak gosterecegim kisim local API ve demo proof. AWS kismi ise maliyet guvenligi nedeniyle kanit dosyalariyla sunulacak."

**Gosterilecek sey:** Dockerized API, S3 artifact store, ECR image, EKS service, local proof.

**Gecis cumlesi:** "Simdi calistigini nasil kanitladigimi gostereyim."

**Sakin deme:** "AWS endpoint su an canli." Eger o gun acmadiysan bunu soyleme.

---

### Slayt 11 - Canli demo kaniti

**Amac:** Hoca ve sinifa projenin gercekten calistigini gostermek.

**Soyleyecegin metin:**

"Bu projede sadece slayt yok. `demo-proof` komutu lokal API'yi acar, model artifact'lerini yukler, endpoint'leri cagirir ve kanit dosyalari uretir. Health, metadata, priorities, record lookup ve score endpoint'leri test edilir."

"Bu raporda model tipi, threshold, skorlanan satir sayisi, priority row sayisi ve ornek skor cevabi gorunuyor. Ornegin score endpoint probability, prediction ve why_risky aciklamasi donduruyor."

"Yani bu, ekranda yazilmis bir proje fikri degil; ayni dosyalardan tekrar calisan bir API prototipi."

**Gosterilecek komut:**

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof
```

**Gosterilecek rapor:**

```bash
cat /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/demo_proof.md
```

**Gecis cumlesi:** "Son olarak hangi kismi tamamladigimi ve hangi kismi bilincli sinir olarak biraktigimi toparlayayim."

**Sakin deme:** "Her sey tam urun seviyesinde hazir." Dogru cumle: "Production'a tasinabilir prototip."

---

### Slayt 12 - Kapanis ve sinirlar

**Amac:** Projeyi abartmadan guclu kapatmak.

**Soyleyecegin metin:**

"Bugun calisan kisim: resmi veri ETL'i, dense panel, leakage audit, calibrated logistic ranking, GEE, Negative Binomial, ANOVA, GLMM diagnostic, why_risky aciklama, FastAPI, Docker, demo proof, final audit ve AWS proof."

"Sinirlar da net: Bu bir heating season modelidir, yaz sicak hava dalgasi modeli degildir. Karar destek prototipidir, otomatik denetim sistemi degildir. AWS endpoint maliyet nedeniyle surekli acik degildir; kanit alip kapatilmistir. Supabase ana sistemden bilincli olarak cikarilmistir, cunku model kalitesine dogrudan katkisi yoktu."

"Benim ana sonucum su: Istatistiksel modelleme, dogru veri tasarimi ve servis mimarisi birlesince, kamu sikayet verisi sadece raporlanan bir veri olmaktan cikiyor; denetim onceligi ureten uygulanabilir bir araca donusuyor."

**Gosterilecek sey:** Bugun calisanlar ve sonraki adimlar.

**Gecis cumlesi:** "Sorulari alabilirim."

**Sakin deme:** "Eksik yok." Dogru cumle: "Canli production degil, audit-ready prototip."

---

### QR brosur slayti

**Amac:** Kagit dagitmadan herkesin brosure erismesi.

**Soyleyecegin metin:**

"Kagit dagitmak yerine bu QR kodu kullaniyorum. Telefonda acilan brosurde problem, veri kaynaklari, yontemler, model bulgulari ve sinirlar tek yerde ozetleniyor. Sunumu dinlerken yontem kismina bakarsaniz logistic regression, ANOVA, Negative Binomial ve validation mantigini lisans seviyesinde gorebilirsiniz."

**Kullanim notu:** Final PPTX/PDF icinde QR slayti bulunuyor. Eger dosyada sonda gorunurse sunumun basinda hizlica o slayta gecip QR'yi okut, sonra tekrar kapaga don.

**Sakin deme:** "QR API dashboard'u acar." Dogru cumle: "QR brosur PDF'ini acar."

---

## 5. Tahtaya yazilacak ana sema

Sunum basinda veya yontem bolumunde tahtaya su akis cizilebilir:

```text
NYC 311 complaints
        +
HPD buildings / violations / heat sensor
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
why_risky + API + dashboard + AWS proof
```

Tahtaya yazilacak problem cumlesi:

```text
Problem:
Sinirli denetim kapasitesi varsa, yarin hangi binalara once gidilmeli?
```

Tahtaya yazilacak hedef degisken:

```text
Y_{building, day+1} = 1  -> Ertesi gun heating/hot water complaint var
Y_{building, day+1} = 0  -> Ertesi gun complaint yok
```

Tahtaya yazilacak logistic regression fikri:

```text
logit(P(Y=1)) =
beta0
+ beta1 * gecmis complaint
+ beta2 * sicaklik / heating degree
+ beta3 * violation gecmisi
+ beta4 * CRE vulnerability
+ ...
```

Tahtaya yazilacak ANOVA hipotezi:

```text
H0: Aylik ortalama complaint yogunluklari esit.
H1: En az bir ayin ortalamasi farkli.

Sonuc:
F = 33.62
p < 0.0001
eta^2 ~= 0.500
```

Tahtaya yazilacak metrik yorumu:

```text
Accuracy degil, ranking onemli:

Precision@50 = Ilk 50 binanin ne kadari gercekten pozitif?
Lift@50 = Ilk 50 liste, rastgele siralamadan kac kat daha iyi?
```

---

## 6. Yontemleri lisans seviyesinde nasil aciklayacaksin?

### Logistic regression

**Ne icin kullandim?**
Ertesi gun complaint olup olmayacagini olasilik olarak tahmin etmek icin.

**Neden uygun?**
Hedef degisken binary: complaint var veya yok.

**Projede ne uretti?**
Her bina-gun icin risk olasiligi, threshold sonucu ve priority ranking.

**Kisa hoca cevabi:**
"Binary hedef icin logistic regression kullandim. Ciktisi olasilik oldugu icin binalari risk skoruna gore siraladim. Ana operasyonel ciktim bu ranking."

---

### ANOVA

**Ne icin kullandim?**
Aylara gore complaint yogunlugunda anlamli fark var mi diye test etmek icin.

**Neden uygun?**
Birden fazla grup var: heat season aylarinin ortalama complaint yogunluklari karsilastiriliyor.

**Projede ne uretti?**
F=33.62, p<0.0001 ve eta²≈0.500. Bu, aylik farkin istatistiksel olarak anlamli ve etki buyuklugunun dikkate deger oldugunu gosterdi.

**Kisa hoca cevabi:**
"ANOVA'yi model kurmadan once mevsimsel farki test etmek icin kullandim. H0 aylik ortalamalar esit diyordu; p<0.0001 ile bunu reddettim."

---

### Negative Binomial

**Ne icin kullandim?**
Complaint sayisi gibi count verisini kontrol etmek icin.

**Neden Poisson yerine Negative Binomial?**
Complaint sayilarinda varyans ortalamadan buyuk olabilir. Bu overdispersion durumunda Negative Binomial daha uygundur.

**Projede ne uretti?**
Binary risk modelini destekleyen count-side istatistiksel kontrol verdi. Yani sadece complaint var/yok degil, complaint sayisi tarafinda da sinyallerin tutarli olup olmadigina bakildi.

**Kisa hoca cevabi:**
"Logistic model binary riski, Negative Binomial ise complaint sayisi tarafini okumak icin kullanildi. Count verisinde overdispersion riski oldugu icin NB daha uygun."

---

### GEE

**Ne icin kullandim?**
Ayni binanin tekrar eden gunleri oldugu icin clustered/repeated observation yapisini daha dogru yorumlamak icin.

**Neden uygun?**
Building-day panelde ayni bina birden fazla kez gorunur. Bu gozlemler tamamen bagimsiz degildir.

**Projede ne uretti?**
CRE, sicaklik ve complaint gecmisi gibi sinyallerin daha yorumlanabilir etkilerini verdi.

**Kisa hoca cevabi:**
"GEE'yi ayni binadan gelen tekrarli gozlemleri dikkate alan yorumlayici istatistiksel model olarak kullandim."

---

### GLMM

**Ne icin kullandim?**
Bina seviyesinde random intercept fikrini diagnostic olarak kontrol etmek icin.

**Neden primary model degil?**
Tam operasyonel ranking icin calibrated logistic model daha sade, hizli ve sunumda savunulabilir. GLMM daha agir ve convergence yorumu dikkat ister.

**Projede ne uretti?**
Mixed-effects bakis acisinin model bulgulariyla celismedigini kontrol eden destekleyici diagnostic.

**Kisa hoca cevabi:**
"GLMM'i ana model olarak degil, bina seviyesindeki heterojenligi kontrol eden diagnostic olarak kullandim. Ana karar listesi logistic ranking ile uretiliyor."

---

### Calibration

**Ne icin kullandim?**
Model skorlarinin olasilik olarak daha okunabilir olmasi icin.

**Neden uygun?**
Bir karar destek sisteminde sadece siralama degil, risk olasiliginin makul yorumlanmasi da onemli.

**Kisa hoca cevabi:**
"Calibration, modelin verdigi skorlarin olasilik yorumu kazanmasi icin kullanildi."

---

### Out-of-time validation

**Ne icin kullandim?**
Modelin sadece ayni donemde degil, sonraki zaman penceresinde de ranking uretip uretmedigini test etmek icin.

**Neden uygun?**
Gercek hayatta model gelecekte kullanilir. Bu nedenle zaman disi test, rastgele splitten daha gercekci bir kontroldur.

**Kisa hoca cevabi:**
"Out-of-time validation, modelin ileriki donem verisinde de ise yarayip yaramadigini gormek icin eklendi."

---

## 7. Demo anlatim metni

Canli demo yapacaksan once terminali temizle:

```bash
cd /Users/omer/aws-analytics-pipeline
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk class-demo-check
```

Soylenecek metin:

"Bu komut sunum oncesi kontrol komutu. Demo proof, final audit, Docker daemon, QR link, e-kampus zip ve local API durumunu kontrol ediyor. Burada `READY` gormem, sinifta gosterecegim dosyalarin ve kanitlarin hazir oldugunu gosteriyor."

Sonra:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof
```

Soylenecek metin:

"Bu komut lokal API'yi calistirip model artifact'lerini yukluyor. Sonra health, metadata, priority list, record lookup ve score endpoint'lerini cagiriyor. Cikan markdown ve JSON dosyalari, projenin ayni artifact'lerle tekrar calistigini kanitliyor."

Raporu ac:

```bash
cat /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/demo_proof.md
```

Rapor uzerinde goster:

- Model type: `logistic_regression`
- Threshold: `0.2`
- Scored rows: yaklasik `8,753,140`
- Priority rows loaded: `50`
- Latest priority date: `2025-05-30`
- Score endpoint probability + prediction + `why_risky`

Dashboard acilacaksa:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk serve
```

Tarayici:

```text
http://127.0.0.1:8000/dashboard?top_n=10
```

Soylenecek metin:

"Bu dashboard denetim ekibi icin hazirlanan okunabilir priority view. API arka planda model ve skor artifact'lerini okuyarak top riskli binalari getiriyor."

Eger tarayici acilmazsa panik yapma. Su cumleyi kur:

"Local server su anda kapali gorunuyor olabilir; bu nedenle kanit raporunu gosteriyorum. `demo-proof` raporu ayni endpoint'lerin calistigini ve yanit dosyalarinin uretildigini kaydetti."

---

## 8. Hoca sorularina kisa ve guvenli cevaplar

### "Tam olarak hangi problemi cozdun?"

"Sinirli denetim kapasitesi problemine odaklandim. Her binaya ayni anda gidilemeyecegi icin, resmi acik verilerle ertesi gun complaint riski yuksek binalari siraladim ve denetim onceligi urettim."

### "Bu proje heat wave modeli mi?"

"Hayir. Bu proje heating season, yani heating/hot water complaint risk modelidir. Yaz heat wave modeli degil. Bunu bilerek net ayirdim."

### "F1 neden cok yuksek degil?"

"Pozitif sinif cok nadir oldugu icin F1 tek basina yeterli degil. Bu nedenle Precision@50, Lift@50, calibration ve out-of-time validation kullandim. Operasyonel soru ilk 50 riskli binada ne kadar dogru risk yakaladigimiz."

### "Ana model hangisi?"

"Ana operasyonel model calibrated logistic ranking. GEE, Negative Binomial ve GLMM destekleyici istatistiksel analiz ve diagnostic amacli."

### "GLMM nerede?"

"GLMM'i primary model olarak degil, bina seviyesinde random intercept mantigini kontrol eden diagnostic olarak kullandim. Ana decision list logistic modelden uretiliyor."

### "ANOVA projede ne ise yaradi?"

"Aylara gore complaint yogunlugu farkli mi diye test etti. H0 aylik ortalamalar esit diyordu. F=33.62 ve p<0.0001 ile aylik farkin anlamli oldugunu gordum."

### "Negative Binomial neden var?"

"Complaint sayisi count verisi oldugu icin ve overdispersion riski tasidigi icin Negative Binomial count-side kontrol modeli olarak kullanildi."

### "Equity veya CRE katmani ne ise yaradi?"

"CRE vulnerability bolgesel kirilganlik bilgisini ekledi. Bunu otomatik karar vermek icin degil, risk siralamasinin sosyal kirilganlik boyutunu daha dikkatli okumak icin kullandim."

### "Veri kaynagin guvenilir mi?"

"Evet. Kaynaklar NYC Open Data, HPD, NOAA GSOD ve Census CRE gibi resmi acik veri kaynaklari. Ayrica veri join ve leakage audit raporlandi."

### "AWS su an canli mi?"

"Maliyet nedeniyle surekli canli tutmuyorum. Canli deploy kaniti alindi, sonra kaynaklar kapatildi. Sinifta local API ve timestamped AWS proof dosyalarini gosteriyorum."

### "Supabase neden yok?"

"Hosted Supabase'i ana kapsamdan cikardim. Cunku model kalitesine dogrudan katkisi yoktu. SQL payload ve schema opsiyonel appendix olarak duruyor ama projenin ana iddiasi degil."

### "Canli urun seviyesinde mi?"

"Tam canli urun sistemi degil; production'a tasinabilir, audit-ready bir karar destek prototipi. Gercek production icin monitoring, guvenlik, SLA, data refresh otomasyonu ve kurum onayi gerekir."

### "Bu sistem denetim kararini otomatik verir mi?"

"Hayir. Bu bir karar destek aracidir. Nihai denetim kararini insan verir; model sadece oncelik listesi ve aciklama uretir."

---

## 9. Riskli cumlelerden kacin

Sunumda kullanma:

- "Bu proje heating problemini cozer."
- "Model kesin olarak hangi binada sorun cikacagini bilir."
- "AWS endpoint su an canli." Eger o gun acmadiysan soyleme.
- "GLMM'i ana karar modeli gibi sunmak."
- "Supabase ana sistemin parcasi."
- "F1 dusuk ama onemli degil." Bunun yerine neden ranking metriklerinin daha uygun oldugunu acikla.
- "Equity ile adil karar verdim." Bunun yerine CRE'yi risk okuma katmani olarak kullandigini soyle.
- "Tam canli urun." Bunun yerine "production'a tasinabilir prototip" de.

Kullanilacak guvenli cumleler:

- "Bu proje denetim onceligi ureten karar destek prototipidir."
- "Ana operasyonel model calibrated logistic ranking'dir."
- "Diger istatistiksel modeller yorum, kontrol ve diagnostic amacli kullanildi."
- "AWS tarafi timestamped proof ile kanitlandi ve maliyet icin kapatildi."
- "Model otomatik karar vermez; insana okunabilir risk siralamasi sunar."

---

## 10. 15 dakikalik kisa versiyon

Eger hoca sureyi kisaltirsa bu akisi kullan:

| Dakika | Anlat |
|---:|---|
| 0-2 | Problem: sinirli denetim kapasitesi, once hangi binalar? |
| 2-4 | Veri: 311, HPD, NOAA, CRE -> building-day panel |
| 4-6 | Leakage audit ve kalite kontrol |
| 6-9 | Logistic regression, ANOVA, GEE/NB/GLMM kisa yontem ayrimi |
| 9-11 | Validation: AUC, P@50, Lift@50, OOT |
| 11-13 | Priority list, why_risky, dashboard |
| 13-15 | Demo proof, AWS proof, sinirlar, kapanis |

Kisa versiyonda mutlaka soyle:

"Bu proje sikayetleri tamamen cozen bir sistem degil; resmi veriye dayali inspection priority list ureten calisan bir karar destek prototipi."

---

## 11. 30 saniyelik kapanis

"Ozetle bu projede resmi acik verileri building-day panelde birlestirdim, leakage audit ile veri sizintisini kontrol ettim, calibrated logistic regression ile ertesi gun complaint riskini siraladim, ANOVA ve diger istatistiksel modellerle bulgulari destekledim. Son cikti, denetim ekipleri icin okunabilir bir priority list ve why_risky aciklamasi. API, Docker ve AWS proof sayesinde proje notebook seviyesinde kalmiyor; servislenebilir bir prototipe donusuyor. En onemli sonuc, sinirli denetim kapasitesinin rastgele degil, veriye dayali ve olculebilir sekilde onceliklendirilmesi."

---

## 12. Dersten once son kontrol listesi

Sunumdan once:

- Ana sunum PDF aciliyor mu?
- PPTX aciliyor mu?
- QR brosur telefonda aciliyor mu?
- `class-demo-check` sonucu `READY` mi?
- `demo-proof` calisiyor mu?
- Docker Desktop acik mi?
- Tarayicida `http://127.0.0.1:8000/dashboard?top_n=10` aciliyor mu?
- E-kampus zip 200 MB altinda mi?
- AWS proof ve shutdown proof dosyalari pakette mi?
- Supabase ana iddia olarak gecmiyor mu?
- "tam canli urun" yerine "production'a tasinabilir prototip" diyorsun mu?

Eger sadece tek kanit gosterecek zaman varsa:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk class-demo-check
```

Ve su raporu ac:

```bash
/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/class_demo_check.md
```

Bu raporda `Overall: READY` gorunmesi, sinifta gosterecegin proje paketinin hazir oldugunu en kisa sekilde kanitlar.
