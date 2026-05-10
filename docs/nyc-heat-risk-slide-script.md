# NYC Heating Complaint Risk
## Slayt Slayt Sunum Metni

Bu dosya, [sunum dosyası](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/outputs/nyc-heating-risk-final/output.pptx) ile birebir uyumlu konuşma metnidir.

Amaç:
- ezberlenebilir olmak
- teknik olarak güçlü durmak
- sınıfa anlaşılır gelmek
- hocanın soru sormasını kolaylaştırmak ama seni zor durumda bırakmamak

Toplam hedef süre:
- `28-30 dakika`

Konuşma temposu:
- hızlı değil
- her slaytta `1 ana fikir`
- her slaytta en fazla `2-3 kritik sayı`

## Sunuma başlamadan önce

Tahtaya en başta şunları yaz:

`building-day`

`next-day risk`

`ranking + interpretability`

`311 + HPD + NOAA + CRE`

Bu dört ifade, sunum boyunca zihinsel omurga olsun.

---

## Slide 1 | Açılış

### Amaç
Projeyi tek cümlede net tanımlamak.

### Birebir söyle

`Ben bu projede New York'ta hangi binaların ertesi gün heating veya hot water complaint üretme riski taşıdığını resmi açık verilerle tahmin eden ve bunu denetim önceliğine çeviren bir kamu analitiği prototipi geliştirdim.`

`Yani sistem arızayı fiziksel olarak tamir etmiyor; hangi binalara önce gidilmesi gerektiğini daha akıllı seçmeye yardım ediyor.`

`Bu yüzden problemim tahmin problemi kadar bir karar problemi.`

### Vurgu yap
- `282,296 complaint`
- `36,170 bina`
- `8,789,310 building-day satırı`

### Geçiş cümlesi

`Ama bu projede asıl kritik nokta veri miktarı değil; hangi kararı iyileştirdiğim.`

---

## Slide 2 | Karar Problemi

### Amaç
Neden sadece F1 konuşmadığını erkenden açıklamak.

### Birebir söyle

`Bu proje tek bir soruya cevap veriyor: Yarın sınırlı denetim kapasitesi varken önce hangi binalara gidilmeli?`

`Burada önemli nokta şu: held-out test döneminde actual positive rate yaklaşık yüzde 0.59.`

`Yani problem çok düşük prevalence'a sahip. Böyle bir ortamda sadece accuracy veya sadece F1 konuşmak eksik olur.`

`Bu yüzden ben başarıyı ranking kalitesi, lift ve yorumlanabilir istatistikle birlikte okudum.`

### Vurgu yap
- `0.59% held-out base rate`
- `Mean P@50 = 0.2743`
- `Lift@50 = 47.34x`

### Sınıfa çeviri

`Daha basit söylersem: modelin ilk 50 önerisinde doğru bina yoğunluğu rastgele seçime göre çok daha yüksek.`

### Geçiş cümlesi

`Bu karar mantığını kurduktan sonra şimdi verinin nasıl birleştiğini göstereceğim.`

---

## Slide 3 | Veri ve Karar Birimi

### Amaç
Neden `building-day` seçtiğini savunmak.

### Birebir söyle

`Bu projede analiz birimim building-day. Yani her bina için her gün ayrı bir gözlem üretiyorum.`

`Bunu seçmemin nedeni şu: hava günlük değişiyor ama müdahale bina düzeyinde yapılıyor.`

`Dolayısıyla bina-gün, hem veri tarafına hem operasyon tarafına aynı anda oturan en doğal birim oldu.`

`Veri akışı da şu şekilde: complaint kayıtları, bina geçmişi, registration ve violation bilgileri, hava verisi ve Census CRE kırılganlık katmanı aynı panelde birleşiyor.`

### Tahtaya yaz

`Risk_it = f(weather_it, history_it, violations_it, vulnerability_i)`

### Kısa savunma cümlesi

`Bu yüzden bu proje sadece dashboard veya geçmiş raporu değil; karar birimi tanımlanmış bir risk sistemi.`

### Geçiş cümlesi

`Ama böyle bir panel kurduğun anda en büyük risk leakage oluyor.`

---

## Slide 4 | Leakage Audit ve Kalite Kontrol

### Amaç
Hocaya veri tarafını ciddiye aldığını göstermek.

### Birebir söyle

`Bu slide bence projenin en önemli savunma slaytlarından biri. Çünkü iyi görünen birçok model aslında leakage yüzünden iyi görünüyor.`

`Ben burada violation snapshot'ı complaint tarihine kadar kestim. Yani model geleceği görmüyor.`

`Sonra dense paneli ayrıca audit ettim.`

`Duplicate row sıfır, future as-of row sıfır, target mismatch sıfır, weather missing sıfır.`

`Dolayısıyla model performansı, yanlış veri akışından değil gerçekten geçmiş bilgiyle tahmin yapmaktan geliyor.`

### Vurgu yap
- `future as-of = 0`
- `label mismatch = 0`
- `weather missing = 0`

### Dürüstlük cümlesi

`Çok küçük bir linked metadata eksiği var ama oran yüzde 0.02 civarında; çekirdek sonucu bozacak büyüklükte değil.`

### Geçiş cümlesi

`Veri güvenilir olduktan sonra artık heat-season davranışını gösterebilirim.`

---

## Slide 5 | Heat-Season Profili

### Amaç
Problem tanımının mevsimle uyumlu olduğunu göstermek.

### Birebir söyle

`Burada özellikle şunu netleştiriyorum: bu proje summer heatwave modeli değil.`

`Benim problemim heating ve hot water complaint riski. O yüzden pencereyi heat-season mantığıyla kurdum: 2024-10-01 ile 2025-05-31 arası.`

`Aylık profil gösteriyor ki en soğuk dönem aynı zamanda en yoğun complaint ve pozitif bina dönemine denk geliyor.`

`Bu yüzden weather değişkenlerini modele eklemek kozmetik değil; doğrudan problem tanımının bir parçası.`

### Vurgu yap
- `En soğuk ay: Jan 2025`
- `Aynı dönemde en yüksek pozitif bina sayısı`

### Geçiş cümlesi

`Ama mevsimsel desen görmek tek başına yetmez; modelin bunu gerçekten kullanılabilir tahmine çevirip çevirmediğini de göstermem gerekir.`

---

## Slide 6 | Validation ve Calibration

### Amaç
Modeli neden daha olgun bir şekilde değerlendirdiğini göstermek.

### Birebir söyle

`Burada modeli tek bir train-test bölmesiyle okumadım.`

`Expanding monthly backtest kullandım, calibration yaptım ve ranking kalitesini ayrıca ölçtüm.`

`Calibration yöntemi Platt. Ayrıca threshold'u da ayrı tuning penceresinde seçtim.`

`Bence burada en önemli sonuç şu: Mean Precision@10 yaklaşık 0.4531, Mean Precision@50 ise 0.2743.`

`Yani model her gün ilk sıralara koyduğu binalarda rastgele seçime göre çok daha yoğun doğru sinyal biriktiriyor.`

`Bunu ileri zamanda, üstelik aynı problem rejiminde de test ettim. 2025-10-01 ile 2026-04-25 arasındaki ikinci heating-season OOT pencerede Mean P@50 yaklaşık 0.6893, Precision 0.4571 ve ROC AUC 0.8107 geldi.`

`Yani ranking sinyali tamamen kaybolmuyor; ama aynı threshold ile karar davranışı bozuluyor.`

### Vurgu yap
- `5 fold`
- `Platt calibration`
- `Brier score = 0.0060`

### Kısa yorum

`Bu yüzden bu projeyi sadece bir classification ödevi gibi değil, bir ranking ve decision support sistemi gibi değerlendirdim.`

### Geçiş cümlesi

`Şimdi bu karar mantığını taşıyan model ailesini göstereceğim.`

---

## Slide 7 | Modeller

### Amaç
Neden birden fazla model kullandığını açıklamak.

### Birebir söyle

`Burada tek model kullanmadım çünkü her model başka bir soruya cevap veriyor.`

`Baseline bana çıplak referans veriyor.`

`Calibrated logistic benchmark tarafında tekrar üretilebilir ve güçlü bir ranking hattı veriyor.`

`GEE logistic clustered inference sağlıyor; çünkü aynı bina tekrar tekrar gözleniyor.`

`GLMM tarafını mixed-effects diagnostic olarak kurdum; ancak ana performans ve çıkarım kanıtını calibrated logistic, GEE ve Negative Binomial taşıyor.`

`Negative Binomial ise next-day complaint count gibi count data için daha uygun.`

`Bu slayttaki tabloyu da bu yüzden böyle okuyorum: Baseline ve calibrated logistic tarafında held-out F1 ve AUC görüyorum; ranking kalitesini ise özellikle P@50 ile okuyorum.`

### Kritik cümle

`Yani ben sadece tahmin değil, hem benchmark hem çıkarım hem de count hedefi için ayrı model mantıkları kullandım.`

### Dürüstlük cümlesi

`GLMM building-panel stratified sample üzerinde çalıştırıldı, fakat VB optimizer tam converge etmediği için bunu ana başarı kanıtı olarak değil diagnostic deneme olarak anlatıyorum.`

### Geçiş cümlesi

`Model ailesi tamam; şimdi hangi değişkenlerin gerçekten anlamlı kaldığını göstereceğim.`

---

## Slide 8 | İstatistiksel Bulgular

### Amaç
Hocaya “yorumlanabilir sonuç” göstermek.

### Birebir söyle

`Bu slide akademik olarak en güçlü slaytlardan biri.`

`Burada weather ve vulnerability terimlerinin modelde anlamlı kaldığını gösteriyorum.`

`Soğuma şoku, heating degree, recent complaint geçmişi ve CRE vulnerability ana çıkarım modeli olan GEE tarafında okunabilir sinyal veriyor.`

`Ayrıca aylık ANOVA da complaint yükünün heat-season boyunca sabit kalmadığını doğruluyor.`

### Vurgu yap
- `GEE CRE OR = 2.5815`
- `GLMM = diagnostic mixed-effects denemesi, ana kanıt değil`
- `ANOVA F = 33.62`
- `ANOVA eta² = 0.500`

### Sınıfa basit anlatım

`Yani kırılganlık, hava ve geçmiş şikayet davranışı birlikte düşünüldüğünde risk anlamlı biçimde yükseliyor.`

`Eta kare değerinin yaklaşık 0.50 çıkması da mevsimsel farkın yalnızca istatistiksel olarak anlamlı değil, aynı zamanda büyük etkili olduğunu gösteriyor.`

### Geçiş cümlesi

`Bu istatistiksel sonuçların sahaya nasıl döndüğünü de göstermek istiyorum.`

---

## Slide 9 | Operasyonel Çıktı

### Amaç
Projenin gerçek faydasını görünür yapmak.

### Birebir söyle

`Bu proje skorda bitmiyor. Son çıktı doğrudan bir inspection priority list.`

`Yani model, ertesi gün ekiplerin önce hangi binalara bakması gerektiğini sıraya koyuyor.`

`Burada son skor tarihi için top 5 binayı görüyorsunuz.`

`Yeni eklediğim why_risky çıktısı sayesinde sadece liste vermiyorum; ilk sıradaki binanın neden riskli görüldüğünü de feature katkılarıyla açıklıyorum.`

`Bu yüzden bu proje sadece analiz veya dashboard değil; karar desteğine dönüşen bir operasyonel çıktı üretiyor.`

### Vurgu yap
- `Top 50 list`
- `avg calibrated risk`
- `Mean P@50`
- `why_risky feature explanation`

### Güçlü cümle

`Benim için projenin gerçek değeri burada: metrikten müdahale sırasına geçebilmesi.`

### Geçiş cümlesi

`Son olarak önce cloud katmanını, sonra da çekirdek analitiğin ne kadarının tamamlandığını ve bu prototipin sınırlarını dürüstçe ayıracağım.`

---

## Slide 10 | Cloud Katmanı

### Amaç
Projeyi yalnızca analiz değil, servislenebilir bir sistem olarak çerçevelemek.

### Birebir söyle

`Bu projede AWS kısmını da düşünerek cloud-ready bir katman hazırladım.`

`Burada mantık şu: model bundle, scored çıktı, priority list ve record lookup artifact'leri S3 üzerinde tutuluyor.`

`FastAPI servisi Docker image olarak paketleniyor, ECR üzerinden taşınıyor ve EKS üzerinde servislenebilecek biçimde hazırlanıyor.`

`Athena external tables bu artifact'lerin AWS tarafında SQL üzerinden sorgulanmasını sağlıyor. Supabase/Postgres katmanı ise top-risk binaları, why_risky açıklamalarını ve demo proof eventlerini normalize operasyon tablolarında tutuyor.`

`Supabase ve AI tarafı modelin başarısını doğrudan artırmıyor. Supabase SQL reporting sağlıyor; AI ise top-risk binalar için neden riskli olduğunu, hangi feature'ların etkili olduğunu ve denetim notunu okunur bir açıklamaya çevirebilir.`

`Bu yüzden AI katmanını karar verici olarak değil, açıklama ve raporlama katmanı olarak konumluyorum.`

`Yani proje sadece analiz dosyaları üreten bir çalışma değil; yerelden cloud ortamına taşınabilecek bir deployment mantığı da taşıyor.`

### Vurgu yap
- `Dockerized API`
- `S3 artifact store`
- `ECR + EKS`
- `Athena external tables`
- `Supabase/Postgres reporting`
- `opsiyonel AI explainer: risk gerekçesi + inspection note`

### Dürüst cümle

`Buradaki ana mesajım, projenin cloud-ready olması. Canlı release son ayrı adım olarak yapılacak.`

### Geçiş cümlesi

`Şimdi önce projenin gerçekten çalıştığını nasıl kanıtlayacağımı göstereceğim; sonra kapanışta sınırları net ayıracağım.`

---

## Slide 11 | Canlı Demo Kanıtı

### Amaç
Projeyi sadece anlattığını değil, gerçekten çalıştırabildiğini göstermek.

### Birebir söyle

`Bu slayt, projenin sunum dosyasından ibaret olmadığını göstermek için var.`

`Burada tek komutla lokal FastAPI servisini açıyorum, model artifact'lerini yüklüyorum ve ana endpointleri çağırıyorum.`

`Health çıktısı model bundle, scored CSV, priority CSV ve SQLite lookup dosyasının yüklendiğini gösteriyor.`

`Ek olarak aynı demo-proof komutu, final çıktının Postgres'e yazılacak normalize Supabase payload'una dönüştüğünü gösteriyor: model run, daily priority buildings, prediction explanations ve demo proof events.`

`Priorities çıktısı son gün için top-N inspection priority list üretiyor.`

`Record lookup çıktısı gerçek bir building-day kaydını building ID ve tarih ile geri getiriyor.`

`Score endpoint'i ise probability, threshold, prediction ve why_risky açıklaması döndürüyor.`

### Göstereceğin komut

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof
```

### Açacağın dosyalar

- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/demo_proof.md`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/priorities_top5.json`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/score_response.json`

### Kritik cümle

`Bu demo, priority list ve API çıktısının aynı eğitilmiş calibrated logistic artifact'inden geldiğini kanıtlıyor.`

### Dürüst cümle

`AWS canlı deploy ayrı ve maliyetli son adım; bu slayt AWS öncesi no-cost çalışma kanıtı.`

### Geçiş cümlesi

`Şimdi artık neyin tamamlandığını ve hangi sınırların kaldığını dürüstçe kapatabilirim.`

---

## Slide 12 | Kapanış

### Amaç
Projeyi güven veren bir dürüstlükle kapatmak.

### Birebir söyle

`Bu slide'da analitiğin tamamlanan kısmı ile sonraki genişleme adımını ayırıyorum.`

`Şu anda proje resmi veri entegrasyonu, leakage audit, ranking, istatistiksel çıkarım, priority list, cloud-ready deployment katmanı ve ikinci heating-season out-of-time validation tarafında gerçekten çalışıyor.`

`Dürüst kalan sınırlılıklar şu: bu prototip heating season odaklı ve sistem karar destek üretiyor; otomatik denetim kararı vermiyor. GLMM tarafında building-panel sample kullanıldı ve VB convergence sınırlılığı var; ana kanıt GEE, calibrated logistic ve NB tarafında.`

`Ama buna rağmen proje sadece model denemesi değil; resmi veri, kalite denetimi, yorumlanabilir çıkarım ve saha önceliği aynı yapıda birleşiyor.`

### Kapanış cümlesi

`Bu çalışma geçmişi raporlayan bir dashboard değil; ertesi gün hangi binaların önce denetlenmesi gerektiğini söyleyen ve cloud katmanına taşınabilecek bir kamu analitiği prototipi.`

---

## Sunum Boyunca Kaçınman Gereken Şeyler

- `Bu proje problemi çözüyor` deme.
  Bunun yerine:
  `Bu proje karar vermeyi iyileştiriyor` de.

- `Model çok başarılı` deme.
  Bunun yerine:
  `Problem düşük prevalence yüzünden zor; buna rağmen ranking tarafında güçlü operasyonel sinyal veriyor` de.

- `Production-ready` deme.
  Bunun yerine:
  `Çalışan prototip ve deploy-ready altyapı` de.

- `Mixed-effects'i full datasette kurdum` deme.
  Çünkü doğru değil.

---

## Hızlı Kurtarıcı Cümleler

Eğer heyecanlanırsan şu kısa cümlelere dön:

`Bu proje bir karar problemi çözüyor.`

`Analiz birimim building-day.`

`Leakage riskini audit ile kapattım.`

`Başarıyı sadece F1 ile okumadım.`

`Asıl değer ranking ve operational priority.`

`Çıktı, ertesi gün için inspection priority list.`

---

## Son Not

Sunumda en çok güven veren şey şudur:

`Ne yaptığını kadar ne yapmadığını da dürüst söylemen.`

Bu projede senin en güçlü tarafın:
- resmi veri kullanman
- leakage audit yapman
- hem benchmark hem inference modeli kurman
- sonucu gerçek bir kamu operasyonuna bağlaman
