# Mentor Taslak Notu

Bu dosya, hocanın istediği maddelere direkt cevap vermek için yazıldı. Proje güncellenecek; şu an amaç çalışan bir iskelet göstermek.

## İstenenler ve Karşılığı

| Hocanın isteği | Bu taslakta karşılığı |
|---|---|
| 5-10 haber sitesi bul | `config/sources.json` içinde 9 kaynak var |
| Haber topla | RSS üzerinden haber başlığı, link, özet, tarih toplanıyor |
| LLM ile içeriği analiz ettir | `llm.py` içinde OpenAI analyzer var |
| Türüne göre ayır | `siyaset`, `ekonomi`, `dunya`, `teknoloji`, `spor`, `saglik`, `kultur`, `hukuk`, `egitim`, `diger` |
| JSONB olarak Postgres'e tek alanda kaydet | `news_documents.payload jsonb` alanı var |
| Structure değişecek | Ana veri tek `payload` içinde tutuluyor; yeni alanlar migration yapmadan eklenebilir |

## Şu An Çalışan Kısım

```bash
cd /Users/omer/aws-analytics-pipeline/projects/news-llm-postgres
source /Users/omer/aws-analytics-pipeline/.venv/bin/activate
make dry-run
```

Son denemede:

- 9 kaynak aktifti.
- 14 haber payload'ı üretildi.
- Çıktı `outputs/latest_payloads.jsonl` dosyasına yazıldı.

## LLM ile Çalıştırma

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
make dry-run-llm
```

API key yoksa fallback analyzer devreye giriyor. Bu sadece demo içindir; asıl analiz LLM ile yapılacak.

## Postgres JSONB

Tablo:

```sql
CREATE TABLE IF NOT EXISTS news_documents (
    id BIGSERIAL PRIMARY KEY,
    content_hash TEXT NOT NULL UNIQUE,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload JSONB NOT NULL
);
```

Postgres çalıştırmak için Docker Desktop açık olmalı:

```bash
make db-up
export DATABASE_URL="postgresql://news:news@localhost:54329/news"
make init-db
make run-db
```

## Neden JSONB?

Haber kaynaklarının alanları ve LLM çıktısı değişebilir. Bugün kategori/özet/etiket tutarken yarın entity, kişi, kurum, lokasyon veya önem skoru eklemek gerekebilir. Bunları ayrı kolonlara bölmek yerine tek `payload jsonb` içinde saklıyorum. Sorgulanması gereken alanlar için sonradan index eklenebilir.

## Eksikler

- Docker Desktop kapalı olduğu için Postgres canlı yazma adımı henüz lokal doğrulanmadı.
- LLM API key ile gerçek analiz henüz denenmedi.
- HTML içeriğin tamamını çekme opsiyonu var ama başlangıçta RSS özetiyle gidiyor.
- Kaynakların robots.txt ve kullanım şartları ayrıca kontrol edilmeli.
- Kategori seti hocayla netleşince güncellenecek.

## Hocaya Atılacak Kısa Mesaj

```text
Hocam haber toplama + LLM analiz + Postgres JSONB için ilk taslak iskeleti hazırladım.

Şu an 9 haber kaynağı config'te var. RSS üzerinden haberleri alıyor, LLM varsa kategori/özet/keyword/sentiment çıkaracak katman var. Sonuçları Postgres'te tek payload jsonb alanına yazacak şekilde tasarladım; yapı değişirse payload genişleyebilir.

Bu bitmiş ürün değil, birlikte güncellemek için ilk taslak.
```
