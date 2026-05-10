# NYC Heating Complaint Risk - Bugün Yapılacaklar

Bu belge, projeyi gerçekten başlatmak için bugünkü minimum ama kritik iş listesidir.

## Günün hedefi

Bugün sonunda şu üç şey netleşmiş olmalı:

1. Resmi veri kaynaklarının indirilebildiği doğrulanmış olacak.
2. İlk `building-day` veri modeline gidecek şema ve join mantığı yazılı olacak.
3. Sınıfta projeyi anlatırken dağıtabileceğin broşür hazır olacak.

## Bugünkü ana görevler

### 1. Starter veri paketini indir

Amaç:
- resmi veri erişimini teknik olarak doğrulamak
- CSV başlıklarını görmek
- ilk örnek çalışma setini oluşturmak

Komut:

```bash
python3 projects/nyc-heat-risk/src/etl/download_official_data.py --limit 1000
```

Beklenen çıktı:
- `projects/nyc-heat-risk/data/raw/` altında starter CSV/TXT dosyaları
- `download_manifest.json`

## 2. Şema notlarını dondur

Amaç:
- hangi alanın hangi tabloda olduğunu kaybetmemek
- join anahtarlarını erkenden netleştirmek

Bugün özellikle bakılacak alanlar:
- `bbl`
- `buildingid` / `building_id`
- `bin`
- `incident_address`
- `housenumber`
- `streetname`
- `created_date`
- `received_date`
- `major_category`
- `novdescription`

Beklenen çıktı:
- `data/schemas/` altında kısa alan notları

## 3. Heat filtre mantığını kesinleştir

Bugün karar ver:

311 tarafında:
- `complaint_type = HEAT/HOT WATER`
- `descriptor` içinde `HEAT` veya `HOT WATER`

HPD Problems tarafında:
- `major_category = HEAT/HOT WATER`

Violation tarafında:
- `novdescription` içinde `NO HEAT`, `HOT WATER`, `NO HEAT AND NO HOT WATER`

Beklenen çıktı:
- tek sayfalık filtre mantığı notu

## 4. İlk join stratejisini yaz

Sıra:

1. `311 / HPD complaints` -> mümkünse `bbl`
2. `bbl` yoksa adres standardizasyonu
3. `buildings` tablosu ile bina omurgası
4. `violations` ve `registrations` ekleme
5. hava verisini tarih bazlı bağlama
6. sosyal kırılganlığı area bazlı bağlama

Bugün SQL yazıp bitirmek zorunda değilsin. Ama join stratejisi netleşmeli.

## 5. İlk feature mart mantığını oku

Başlangıç dosyaları:
- [01_stg_311_heat_requests.sql](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/sql/01_stg_311_heat_requests.sql)
- [02_fct_building_day_heat_risk.sql](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/sql/02_fct_building_day_heat_risk.sql)
- [03_validation_queries.sql](/Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk/sql/03_validation_queries.sql)

Bugün cevaplanacak soru:
- `surge_flag` için başlangıç eşiği 3 mü, 2 mi, yüzdelik tabanlı mı?

## 6. Broşürü gözden geçir

Amaç:
- sınıftakiler sen anlatırken kaybolmasın
- proje dinleyici tarafında da anlaşılır olsun

Kontrol et:
- problem çok teknik mi yazılmış?
- "bu neye yarıyor?" sorusuna net cevap var mı?
- veri kaynakları güven veriyor mu?

## Bugün bitince elinde olması gerekenler

- indirilen starter veri setleri
- bir sayfalık filtre mantığı notu
- ilk join taslağı
- broşür/handout
- yarın için net görev listesi

## Bugün yetişmezse öncelik sırası

1. Veri indirme scripti çalışsın
2. Heat filtre mantığı kesinleşsin
3. Bina join stratejisi yazılsın
4. Broşür son rötuş
5. Modeling detayları yarına kayabilir
