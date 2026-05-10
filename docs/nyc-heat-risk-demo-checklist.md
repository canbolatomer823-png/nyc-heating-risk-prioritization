# NYC Heating Complaint Risk

## Derste Çalıştığını Kanıtlama Checklist'i

Bu checklist'in amacı projeyi üç katmanda kanıtlamaktır:

1. Gerçek ve resmi veri kullanıldı.
2. Kod gerçekten çalışıyor.
3. Çıktı karar destek sistemine dönüşüyor.

Bu dosyayı sunumdan önce bir kez prova ederek kullan.

---

## 1. Dersten Önce Hazırlık

Sunumdan önce şunlar hazır olsun:

- Sunum dosyası
- Broşür
- Terminal açık
- Proje klasörü hazır
- İnternet olmasa bile yerel artifact'ler erişilebilir olsun

Kontrol edilecek ana dosyalar:

- `projects/nyc-heat-risk/outputs/nyc-heating-risk-final/output.pptx`
- `projects/nyc-heat-risk/outputs/nyc-heating-brochure-final/output.pptx`
- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/heat_data_profile.md`
- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/logistic_regression_metrics.md`
- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/statistical_model_metrics.md`
- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_summary.md`
- `projects/nyc-heat-risk/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_validation.md`

---

## 2. En Güçlü 5 Dakikalık Demo

### Adım 1: Proje problemini söyle

Şu cümleyle aç:

> Bu proje, ertesi gün hangi binalarda heating veya hot water şikayeti oluşma riskinin yüksek olduğunu resmi verilerle tahmin ediyor ve bunu denetim öncelik listesine çeviriyor.

### Adım 2: Resmi veri kullandığını göster

Şu dosyayı aç:

- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/heat_data_profile.md`

Vurgula:

- veri penceresi: `2024-10-01 -> 2025-05-31`
- complaint sayısı
- bina sayısı
- dense panel boyutu
- weather ve CRE coverage

Söylenecek kısa cümle:

> Veri uydurma değil; NYC 311, HPD, NOAA ve Census kaynaklarından geliyor.

### Adım 3: Kodun gerçekten çalıştığını göster

Terminalde sırayla çalıştır:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk test
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk smoke
```

Beklenen kanıt:

- `16 tests OK`
- `local smoke test passed`

Söylenecek kısa cümle:

> Yani bu sadece slayt değil; test edilen ve ayakta çalışan bir sistem.

### Adım 4: Model çıktısını göster

Şu dosyaları aç:

- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/logistic_regression_metrics.md`
- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/statistical_model_metrics.md`

Vurgula:

- calibrated logistic
- GEE
- GLMM diagnostic
- Negative Binomial
- `P@50`, `ROC AUC`, `F1`

Söylenecek kısa cümle:

> Burada prediction ve inference tarafını birlikte kullandım; sadece kara kutu model kurmadım.

### Adım 5: İstatistik tarafını göster

Şu dosyaları aç:

- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/seasonal_anova.md`
- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/r_statistical_replication.md`

Vurgula:

- ANOVA ile aylık fark
- `F`, `p`, `eta^2`
- R ile replikasyon

Söylenecek kısa cümle:

> Model sadece tahmin üretmiyor; mevsimsel farkın anlamlı olup olmadığını da test ediyorum.

### Adım 6: Operasyonel çıktıyı göster

Şu dosyayı aç:

- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_latest_day.csv`

Vurgula:

- tarih
- building id
- borough
- probability
- rank

Söylenecek kısa cümle:

> Bu çıktı, denetim ekibinin ertesi gün ilk hangi binalara gitmesi gerektiğini söylüyor.

### Adım 7: Modern DS tarafını göster

Şu dosyaları aç:

- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_policy_simulation.md`
- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/subgroup_fairness_calibration.md`
- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/train_test_drift_report.md`
- `projects/nyc-heat-risk/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_validation.md`

Vurgula:

- policy simulation
- fairness / calibration
- drift
- out-of-time validation

Söylenecek kısa cümle:

> Proje sadece metrik üretmiyor; operasyonel etkiyi, zaman içindeki bozulmayı ve adalet tarafını da inceliyor.

---

## 3. API ile Canlı Mini Demo

İstersen terminalde şu akışı kullan:

```bash
cd /Users/omer/aws-analytics-pipeline
export NYC_HEAT_MODEL_BUNDLE=/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/models/logistic_regression_bundle.joblib
export NYC_HEAT_SCORED_CSV=/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/processed/logistic_regression_scored.csv
export NYC_HEAT_RECORD_LOOKUP_DB=/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/processed/record_lookup.sqlite
./.venv/bin/uvicorn api.app:app --app-dir /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/src --host 127.0.0.1 --port 8012
```

Ayrı terminalde:

```bash
curl http://127.0.0.1:8012/health
curl http://127.0.0.1:8012/metadata
curl "http://127.0.0.1:8012/priorities/latest?top_n=5"
curl "http://127.0.0.1:8012/records/65175?calendar_date=2025-05-30"
```

İstersen skor örneği:

```bash
curl -X POST "http://127.0.0.1:8012/score" \
  -H 'content-type: application/json' \
  -d '{"rows":[{"building_id":"642725","borough":"QUEENS","management_program":"unknown","complaint_count":4,"unique_request_count":4,"no_heat_count":4,"hot_water_problem_count":0,"lag_1_complaints":3,"rolling_3d_complaints":8,"rolling_7d_complaints":15,"rolling_7d_request_count":15,"complaint_day_count_prior":12,"cumulative_complaints_prior":130,"cumulative_request_count_prior":130,"prior_max_daily_complaints":9,"days_since_last_complaint":1,"registration_active_flag":1,"heat_sensor_program_flag":0,"heat_sensor_active_flag":0,"heat_sensor_unit_count":0,"total_linked_violation_count":0,"open_linked_violation_count":0,"unit_count_proxy":20,"weather_avg_temp_c":0.97,"weather_max_temp_c":6.0,"weather_min_temp_c":-3.0,"weather_prcp_mm_mean":0.0,"weather_prcp_mm_max":0.0,"weather_wind_mps_mean":4.0,"weather_heating_degree_c":17.0,"weather_freezing_any_flag":1,"weather_temp_drop_c":4.7,"weather_cold_shock_flag":1}]}'
```

---

## 4. 30 Saniyelik Yedek Kanıt

Terminal veya internet bozulursa sadece şunları aç:

- `projects/nyc-heat-risk/outputs/nyc-heating-risk-final/output.pptx`
- `projects/nyc-heat-risk/outputs/nyc-heating-brochure-final/output.pptx`
- `projects/nyc-heat-risk/data/windows/heat_season_2024_10_01_2025_05_31/reports/inspection_priority_summary.md`
- `projects/nyc-heat-risk/data/windows/oot_heat_season_2025_10_01_2026_04_26/reports/out_of_time_validation.md`

Ve şunu söyle:

> Bu proje resmi verilerle kurulmuş, test edilmiş, istatistiksel olarak değerlendirilmiş ve çalışan API ile öncelik listesi üreten uçtan uca bir karar destek prototipidir.

---

## 5. Hoca Sorarsa Kısa Cevaplar

### Bu proje tam olarak neyi çözüyor?

Sınırlı denetim kapasitesi varken ertesi gün önce hangi binalara gidilmesi gerektiğini veriyle önceliklendiriyor.

### Bu sadece makine öğrenmesi mi?

Hayır. Prediction ve operational ranking için calibrated logistic, inference için GEE, count outcome için Negative Binomial, hipotez testi için ANOVA kullandım. GLMM'i diagnostic mixed-effects kontrolü olarak tuttum; ana kanıt değil.

### Neden F1 düşük ama projeyi yine de savunuyorsun?

Çünkü problem çok düşük prevalanslı. Bu yüzden operasyonel değerlendirmede `Precision@50`, `lift`, policy simulation ve out-of-time ranking daha anlamlı.

### AWS olmadan proje çalışıyor mu?

Evet. AWS sadece cloud deployment katmanı. Veri, model, test, rapor ve API zaten yerelde çalışıyor.

### Supabase bu projede neyi kanıtlıyor?

Supabase model eğitmez ve AWS'nin yerine geçmez. Final top-risk bina listesi, `why_risky` açıklamaları, model run bilgisi ve demo proof eventleri Postgres tablolarına yazılabilecek hale gelir. Böylece çıktıların SQL ile sorgulanabilen operasyonel bir katmana taşındığı gösterilir.

### En dürüst sınırlılık nedir?

Prototip heating-season odaklı ve karar destek aracıdır; otomatik denetim sistemi değildir. GLMM tarafında convergence sınırlılığı var ve canlı AWS deploy maliyet nedeniyle son adıma bırakıldı.

---

## 6. Son Cümle

Kapanışı şu cümleyle yap:

> Bu projede sadece bir model eğitmedim; resmi veriden başlayıp veri kalitesi denetimi, istatistiksel analiz, operasyonel önceliklendirme, fairness ve drift kontrolü ile çalışan bir karar destek sistemi kurdum.
