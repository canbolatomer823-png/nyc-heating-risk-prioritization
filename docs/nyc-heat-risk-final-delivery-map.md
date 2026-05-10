# NYC Heating Risk - Final Teslim ve Paylasim Haritasi

**Ogrenci:** Omer Canbolat
**Numara:** 22050622
**Sunum tarihi:** 12 Mayis
**Amac:** Projede hangi dosyanin nerede kullanilacagini netlestirmek ve yanlis dosya yukleme riskini azaltmak.

---

## 1. Sinifta acilacak ana dosya

**Ana sunum PDF**

```text
/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/outputs/nyc-heating-risk-final/output_with_qr.pdf
```

Kullanim:

- Akilli tahtada veya kendi laptopunda bu PDF'i ac.
- QR slaytinda sinifa brosuru telefondan acabileceklerini soyle.
- Slaytlari okumaya calisma; her slaytta tek ana mesaj ver.

Yedek PPTX:

```text
/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/outputs/nyc-heating-risk-final/output_with_qr.pptx
```

---

## 2. Sinifin QR ile acacagi dosya

**Brosur PDF**

```text
/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/outputs/nyc-heating-brochure-final/output.pdf
```

Kullanim:

- Kagit dagitmak yerine QR ile acilacak.
- Proje problemi, veri kaynaklari, istatistiksel yontemler, model ciktisi ve sinirlar bu dosyada.
- Hoca yontem sorarsa brosurdeki logistic regression / ANOVA / Negative Binomial / GEE-GLMM sayfasina yonel.

Not:

- QR linki presigned URL oldugu icin suresiz degil.
- 12 Mayis sunumu icin mevcut audit geciyor; daha gec sunum olursa QR yeniden uretilmeli.

---

## 3. E-kampus / ders sistemi icin yuklenecek paket

**Teslim ZIP**

```text
/Users/omer/Downloads/NYC_Heating_Risk_Ekampus_Teslim_Omer_Canbolat_22050622.zip
```

Durum:

- Boyut yaklasik `2.2 MB`.
- 200 MB sinirinin cok altinda.
- Ders sistemine tum proje klasoru degil, bu ZIP yuklenmeli.

---

## 4. Staj / CV / link isteyen formlar icin

**Public GitHub linki**

```text
https://github.com/canbolatomer823-png/nyc-heating-risk-prioritization
```

Bu link neyi gosterir?

- Guvenli public portfolio versiyonu.
- Raw veri, .env, AWS credential, kubeconfig, presigned QR link ve buyuk local artifact icermez.
- Kod, test, rapor, SQL, Docker/K8s dosyalari ve portfolio dokumanlari vardir.

**CV PDF**

```text
/Users/omer/Downloads/Omer_Canbolat_CV.pdf
```

**CV DOCX**

```text
/Users/omer/Downloads/Omer_Canbolat_CV.docx
```

Basvuru formu PDF kabul ediyorsa PDF yukle.

---

## 5. Derste calistigini kanitlamak icin komutlar

Once hizli kontrol:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk class-demo-check
```

Beklenen:

```text
Overall: READY
```

Sonra demo proof:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof
```

Rapor:

```text
/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/demo_proof/demo_proof.md
```

Dashboard acmak istersen:

```bash
make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk serve
```

Tarayici:

```text
http://127.0.0.1:8000/dashboard?top_n=10
```

Onemli:

- `127.0.0.1` sadece senin laptopundur.
- Server kapaliysa tarayicida hata almak normaldir.
- `make serve` calisirken dashboard acilir.

---

## 6. Teknik kanit dosyalari

Final audit:

```text
/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/final_project_audit.md
```

Class demo check:

```text
/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/class_demo_check.md
```

AWS live proof:

```text
/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/aws_live_deploy_proof.md
```

AWS shutdown proof:

```text
/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/reports/aws_shutdown_proof.md
```

Sunumda AWS icin dogru cumle:

> AWS live proof alindi; maliyet dogmamasi icin kisa sureli EKS kaynaklari kapatildi. Su an surekli acik public endpoint iddiasi yapmiyorum.

---

## 7. Asla yuklenmeyecek / paylasilmayacak dosyalar

Asagidaki dosya veya klasorleri GitHub'a, e-kampuse veya formlara yukleme:

- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/data/`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/aws.env`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/supabase.env`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/generated-kubeconfig.yaml`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/deploy/rendered/`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/infra/terraform/terraform.tfvars`
- `/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/outputs/nyc-heating-brochure-final/brochure_presigned_url.txt`
- Tum `__pycache__/`, `.pyc`, `.log`, `.DS_Store` dosyalari

Sebep:

- Buyuk veri veya generated artifact olabilir.
- Credential, account id, kubeconfig, presigned URL veya local makineye ozel bilgi icerebilir.
- Public paylasim icin guvenli kaynak zaten GitHub portfolio reposudur.

---

## 8. Son karar

Kisa cevap:

- **Sinifta:** `output_with_qr.pdf`
- **QR ile:** brosur PDF
- **E-kampuste:** `NYC_Heating_Risk_Ekampus_Teslim_Omer_Canbolat_22050622.zip`
- **Staj formunda:** GitHub linki + CV PDF
- **Teknik kanitta:** `class-demo-check`, `demo-proof`, `final_project_audit.md`
- **Yuklenmeyecek:** full local proje klasoru, raw data, env, kubeconfig, rendered deploy ciktisi
