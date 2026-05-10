# NYC Heating Complaint Risk
## 30 Dakikalık Prova Metni

Bu dosya, final sunum için daha doğal konuşma diline çekilmiş prova sürümüdür.

İlgili sunum:
- [Final sunum PPTX](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/outputs/nyc-heating-risk-final/output.pptx)

Ana strateji:
- her slaytta `1 ana fikir`
- her slaytta en fazla `2-3 sayı`
- teknik terimi söyledikten sonra bir cümle sade Türkçe çeviri ver

Toplam süre hedefi:
- `28-30 dakika`

## Sunumdan önce tahtaya yaz

`building-day`

`next-day risk`

`ranking + interpretability`

`311 + HPD + NOAA + CRE`

`prediction + inference + decision`

---

## Slide 1 | Açılış

`Ben bu projede New York'ta hangi binaların ertesi gün heating veya hot water complaint üretme riskinin yüksek olduğunu resmi açık verilerle tahmin eden ve bunu denetim önceliğine çeviren bir kamu analitiği prototipi geliştirdim.`

`Yani bu sistem arızayı tamir etmiyor; sınırlı ekip varken önce hangi binalara gidilmesi gerektiğini daha akıllı seçmeye yardım ediyor.`

`Bu yüzden proje yalnızca bir tahmin problemi değil, aynı zamanda bir karar problemi.`

Vurgu:
- `282,296 complaint`
- `36,170 bina`
- `8,789,310 building-day`

Geçiş:

`Ama burada asıl kritik olan veri büyüklüğü değil, hangi kararı iyileştirdiğim.`

---

## Slide 2 | Karar Problemi

`Bu projenin temel sorusu şu: Yarın denetim kapasitesi sınırlıyken önce hangi binalara gidilmeli?`

`Held-out test döneminde actual positive rate yaklaşık yüzde 0.59. Yani problem düşük prevalence'lı bir problem.`

`Bu yüzden başarıyı sadece F1 ile okumadım; ranking kalitesi, lift ve yorumlanabilir istatistiksel sonuçlarla birlikte değerlendirdim.`

Sade çeviri:

`Benim için önemli olan, modelin ilk sıralara gerçekten doğru binaları taşıyıp taşımadığı.`

Vurgu:
- `P@50 = 0.2743`
- `Lift@50 = 47.34x`

Geçiş:

`Bu karar mantığını kurduktan sonra şimdi veriyi hangi birimde topladığımı göstereceğim.`

---

## Slide 3 | Veri ve Karar Birimi

`Analiz birimim building-day. Yani her bina için her gün ayrı bir gözlem var.`

`Bunu seçmemin nedeni şu: hava günlük değişiyor ama müdahale bina düzeyinde yapılıyor.`

`Dolayısıyla bina-gün birimi hem veri mantığına hem operasyon mantığına aynı anda oturuyor.`

Tahtaya yaz:

`Risk_it = f(weather_it, history_it, violations_it, vulnerability_i)`

`Y1 = next_day_positive_flag`

`Y2 = next_day_complaint_count`

`311, HPD, NOAA ve Census CRE verilerini aynı panelde birleştirdim.`

Geçiş:

`Ama böyle bir panel kurunca en büyük risk leakage oluyor.`

---

## Slide 4 | Leakage Audit

`Bence bu slayt projenin en önemli savunma slaytlarından biri. Çünkü sahte iyi görünen birçok model aslında leakage yüzünden iyi görünür.`

`Ben violation feature'larını complaint tarihine kadar sınırladım. Yani model geleceği görmüyor.`

`Sonra dense paneli audit ettim. Future as-of leakage sıfır, label mismatch sıfır, weather missing sıfır.`

Sade çeviri:

`Kısacası model yanlış veri akışından değil, gerçekten geçmiş bilgiyle tahmin yapıyor.`

Geçiş:

`Veri akışı güvenli olduktan sonra artık heat-season davranışını gösterebilirim.`

---

## Slide 5 | Heat-Season Profili

`Burada özellikle şunu netleştiriyorum: bu proje summer heatwave modeli değil.`

`Benim problemim heating ve hot water complaint riski. O yüzden veri penceremi 2024-10-01 ile 2025-05-31 arasındaki heat-season mantığıyla kurdum.`

`Aylık profil, en soğuk dönemin aynı zamanda en yoğun complaint dönemine yaklaştığını gösteriyor.`

`Bu yüzden weather feature eklemek sadece süs değil; problem tanımının doğrudan bir parçası.`

Geçiş:

`Ama mevsim deseni görmek yetmez; modelin bunu kullanılabilir tahmine çevirip çevirmediğini de göstermem gerekir.`

---

## Slide 6 | Validation ve Calibration

`Burada modeli tek bir train-test bölmesiyle okumadım.`

`Expanding monthly backtest kullandım, calibration yaptım ve ranking kalitesini ayrıca ölçtüm.`

`Calibration yöntemi Platt. Threshold'u da ayrı tuning penceresinde seçtim.`

`En önemli sonuç şu: Mean Precision@10 yaklaşık 0.4531, Mean Precision@50 yaklaşık 0.2743.`

`Yani model, günlük top listede rastgele seçime göre çok daha yoğun doğru bina biriktiriyor.`

`Ayrıca bu metriklerin güven aralığını da çıkardım. P@50 için yüzde 95 güven aralığı yaklaşık 0.233 ile 0.322 arasında.`

`Bir de bunu bir sonraki gerçek heating-season penceresinde test ettim. 2025-10-01 ile 2026-04-25 arasındaki ikinci sezon OOT pencerede Mean P@50 yaklaşık 0.6893, Precision 0.4571 ve ROC AUC 0.8107 geldi.`

`Yani ranking sinyali tamamen kaybolmuyor ama aynı threshold ile karar davranışı bozuluyor. Bu da yeniden calibration veya threshold review gerektiğini gösteriyor.`

Geçiş:

`Şimdi bu ranking mantığını taşıyan model ailesini göstereceğim.`

---

## Slide 7 | Modeller

`Burada tek model kullanmadım çünkü her model başka bir soruya cevap veriyor.`

`Baseline bana çıplak referans veriyor.`

`Calibrated logistic operasyonel benchmark ve ranking hattı veriyor.`

`GEE logistic, aynı binanın tekrar tekrar gözlenmesi nedeniyle clustered inference veriyor.`

`GLMM tarafını random-intercept diagnostic olarak tuttum; convergence sınırı nedeniyle ana kanıt yapmıyorum.`

`Negative Binomial ise next-day complaint count için count model sağlıyor.`

Kısa savunma:

`Yani ben tek model değil, problem yapısına uygun bir model ailesi kurdum.`

Dürüst not:

`GLMM tarafını building-panel stratified sample üzerinde diagnostic olarak çalıştırdım; convergence sınırlılığı olduğu için ana başarı kanıtı yapmıyorum.`

Geçiş:

`Şimdi hangi değişkenlerin gerçekten anlamlı kaldığını göstereceğim.`

---

## Slide 8 | İstatistiksel Bulgular

`Bu slide akademik olarak en güçlü slide. Çünkü burada sadece tahmin değil, yorum da yapabiliyorum.`

`CRE vulnerability ana çıkarım modeli olan GEE tarafında pozitif kaldı.`

`GEE tarafında effect yaklaşık 2.58x.`

`Recent complaint flag, heating degree ve count carry-over da anlamlı sinyal veriyor.`

`Ayrıca ANOVA ile aylık complaint yükünün sabit olmadığını test ettim. F=33.62 ve eta-kare yaklaşık 0.50.`

Sade çeviri:

`Yani mevsim etkisi gerçek, vulnerability gerçek ve yakın geçmiş complaint davranışı da gerçekten bilgi taşıyor.`

Geçiş:

`Bu istatistiksel bulguların operasyonel karşılığı ne, şimdi onu göstereceğim.`

---

## Slide 9 | Operasyonel Çıktı

`Modelin çıktısı sadece skor değil; doğrudan bir denetim önceliği listesi.`

`Son test gününde ilk 5 bina burada görünüyor.`

`Ama daha önemlisi, policy simulation ile günlük kapasite senaryolarını da ölçtüm.`

`Örneğin kapasite 50 olduğunda model günde yaklaşık 13.71 doğru bina yakalıyor.`

`Aynı kapasitede history baseline yaklaşık 7.59, random beklenti ise 0.30 civarında.`

`Equity-weighted liste de yaklaşık 13.80 ile benzer operasyonel güç veriyor ama kırılgan binaları biraz daha öne çekiyor.`

Sade çeviri:

`Yani bu sistem sadece risk söylemiyor; kurumun sınırlı kapasitesini daha verimli kullanmasına yardım ediyor.`

Geçiş:

`Son olarak önce cloud katmanını, sonra projeyi canlı nasıl kanıtlayacağımı ve hangi noktada dürüst sınırlılık bıraktığımı ayıracağım.`

---

## Slide 10 | Cloud Katmanı

`Bu projeyi sadece analiz dosyaları üreten bir çalışma olarak bırakmadım; AWS tarafına taşınabilecek cloud-ready bir katman da hazırladım.`

`Burada model bundle, scored çıktı, priority list ve lookup artifact'leri S3 üzerinde tutuluyor.`

`FastAPI servisi Docker image olarak paketleniyor, ECR üzerinden taşınıyor ve EKS üzerinde servislenebilecek biçimde hazırlanıyor.`

`Athena external tables ile bu artifact'ler AWS tarafında SQL üzerinden sorgulanabiliyor. Supabase/Postgres katmanı ise final top-risk tabloyu, why_risky açıklamalarını ve demo proof eventlerini operasyonel SQL tablosu olarak tutuyor.`

Sade çeviri:

`Yani proje sadece istatistik değil; aynı zamanda deploy düşüncesi olan modern bir veri bilimi prototipi.`

Geçiş:

`Şimdi projenin çalıştığını tek komutla nasıl kanıtlayacağımı göstereceğim.`

---

## Slide 11 | Canlı Demo Kanıtı

`Bu slayt projenin sadece sunum dosyası olmadığını kanıtlamak için var.`

`Tek komutla lokal FastAPI servisini açıyorum, model artifact'lerini yüklüyorum ve ana endpointleri çağırıyorum.`

Komut:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof
```

`Health çıktısı model bundle, scored CSV, priority CSV ve SQLite lookup dosyasının yüklendiğini gösteriyor.`

`Aynı demo-proof komutu final çıktıyı Postgres'e yazılacak normalize Supabase payload'una da çeviriyor: model run, daily priority buildings, prediction explanations ve demo proof events.`

`Priorities çıktısı son gün için top-N inspection priority list üretiyor.`

`Score response ise probability, threshold, prediction ve why_risky açıklaması döndürüyor.`

Kısa savunma:

`Bu demo, priority list ve API çıktısının aynı eğitilmiş calibrated logistic artifact'inden geldiğini kanıtlıyor.`

Geçiş:

`Şimdi artık neyin tamamlandığını ve hangi sınırların kaldığını kapatabilirim.`

---

## Slide 12 | Kapanış

`Bu projede resmi veri entegrasyonu, leakage audit, ranking, istatistiksel çıkarım, operasyonel simülasyon, hata analizi, belirsizlik raporu, drift raporu, cloud-ready deployment katmanı ve ikinci sezon out-of-time validation aynı akışta birleşti.`

`Yani bu çalışma sadece dashboard değil; ertesi gün denetim sırasını üreten bir kamu analitiği prototipi.`

`Dürüst kalan sınırlılıklarım şunlar: proje heating season odaklı, GLMM diagnostic tarafında VB convergence sınırlılığı var ve canlı AWS deploy'u maliyet nedeniyle en sona bırakıldı.`

`Ama AWS hariç çekirdek analitik sistem şu anda çalışır ve savunulabilir durumda.`

Final cümlesi:

`Kısacası ben bu projede sadece model kurmadım; resmi verilerle ertesi gün hangi binalara önce gidilmesi gerektiğini sayısal olarak savunabilen bir karar destek sistemi kurdum.`

---

## Soru Gelirse

### F1 neden çok yüksek değil?

`Çünkü veri gerçek dünya verisi ve prevalence çok düşük. Bu yüzden proje değerini yalnızca sınıflandırma F1'ında değil, ranking, lift ve operasyonel yakalama oranında okuyorum.`

### Equity gerçekten var mı?

`Evet. Census CRE vulnerability dense panele entegre edildi; GEE tarafında pozitif sinyal verdi. Ayrıca equity-weighted priority list ürettim.`

### ANOVA ne işe yaradı?

`ANOVA'yı tahmin için değil, heat-season boyunca complaint yükünün aylara göre anlamlı değişip değişmediğini test etmek için kullandım.`

### Neden bu proje klişe değil?

`Çünkü sadece dashboard veya gecikme tahmini değil; resmi veri, leakage audit, calibrated ranking, clustered inference, GLMM diagnostic, ANOVA, policy simulation ve denetim önceliği aynı yapıda birleşiyor.`
