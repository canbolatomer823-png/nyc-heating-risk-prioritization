# CV and Interview Text

## CV Project Entry

**NYC Heating Complaint Risk Prioritization**  
Built a reproducible data science prototype using official NYC 311, HPD, NOAA and Census CRE data to predict next-day heating/hot-water complaint risk at building-day level. Developed calibrated logistic ranking, ANOVA, Negative Binomial diagnostics, validation/backtesting reports, FastAPI scoring API, Dockerized demo and AWS deployment proof workflow.

## Short Interview Pitch

I built a public analytics project that answers a practical inspection-capacity question: if the city cannot inspect every building tomorrow, which buildings should be prioritized first? I used official NYC open data, built a building-day panel, trained a calibrated logistic ranking model, and added statistical checks such as ANOVA, Negative Binomial diagnostics, panel diagnostics, calibration, drift and out-of-time validation. The output is not an automatic enforcement decision; it is an interpretable priority list with evidence reports and a local FastAPI/Docker demo.

## Turkish Interview Pitch

Bu projede temel sorum şuydu: denetim kapasitesi sınırlıysa, ertesi gün önce hangi binalara bakılmalı? NYC 311, HPD, NOAA ve Census CRE resmi açık verilerini birleştirerek building-day panel oluşturdum. Ana model olarak calibrated logistic regression ile ertesi gün şikayet olasılığını tahmin ettim ve bunu Top-50 denetim öncelik listesine çevirdim. ANOVA ile mevsimsel farkı, Negative Binomial ile şikayet sayısı tarafını, GEE/GLMM diagnostic ile tekrar eden bina yapısını kontrol ettim. Sonuç otomatik karar sistemi değil; açıklanabilir bir karar destek prototipi.

## If They Ask Why Raw Data Is Not Included

The project uses large public-data artifacts and deployment-sensitive environment files. This public repository intentionally includes safe review materials only: code, presentation assets, model/data cards and evidence reports. Raw data, credentials and environment files are excluded.
