# News LLM Postgres Draft

Bu klasör haber toplama işi için ilk taslak. Bitmiş bir uygulama değil; hocayla üzerinden konuşup güncellemek için hazırladım.

Şimdilik yaptığı şey:

- 9 haber kaynağını config dosyasından okuyor.
- Normal web sayfasından haber linklerini buluyor.
- Haber sayfasına girip başlık, açıklama, tarih ve paragraf metni çekmeye çalışıyor.
- LLM varsa kategori, özet, keyword ve sentiment çıkaracak yapı var.
- API key yoksa akışı test etmek için basit fallback analyzer çalışıyor.
- Sonucu Postgres'te tek `payload jsonb` alanına yazacak şekilde tasarlandı.

Kısa mentor özeti için: [MENTOR_DRAFT.md](MENTOR_DRAFT.md)

Ne yaptığımızı öğrenmek için: [LEARNING_NOTES.md](LEARNING_NOTES.md)

Kapsam:

- Haber kaynakları config dosyasından yönetiliyor.
- İlk sürüm normal HTML crawling ile gidiyor.
- HTML'den tam metin çekme kısmı sonradan geliştirilebilir.
- Ham haber ve analiz sonucu aynı JSONB payload içinde tutuluyor.
- Çıktı yapısı değişirse tabloyu sürekli değiştirmek gerekmiyor.

## Mimari

```text
config/sources.json
        |
        v
HTML listing crawler
        |
        v
Article page fetch + text extraction
        |
        v
RawNewsItem
        |
        v
LLM analyzer
        |
        v
JSONB payload
        |
        v
Postgres news_documents(payload jsonb)
```

## Kaynaklar

Başlangıç config'i 9 kaynak içerir:

- BBC Türkçe
- Euronews Türkçe
- Habertürk
- TRT Haber
- Bloomberg HT
- Anadolu Ajansı
- DW Türkçe
- Mynet Haber
- Ensonhaber

Bazı haber siteleri Cloudflare, header uyumsuzluğu veya bot koruması kullanabilir. Pipeline kaynak bazında hata yakalar ve diğer kaynaklarla devam eder.

## Kurulum

Bu proje kendi requirements dosyasını kullanır:

```bash
cd /Users/omer/aws-analytics-pipeline/projects/news-llm-postgres
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Mevcut workspace venv kullanılacaksa:

```bash
cd /Users/omer/aws-analytics-pipeline/projects/news-llm-postgres
source /Users/omer/aws-analytics-pipeline/.venv/bin/activate
python -m pip install -r requirements.txt
```

## Dry Run

LLM API key olmadan web crawling + rule-based fallback analyzer ile payload üret:

```bash
make dry-run
```

Çıktı:

```text
outputs/latest_payloads.jsonl
```

## OpenAI ile Çalıştırma

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
make dry-run-llm
```

API key yoksa pipeline otomatik olarak fallback analyzer kullanabilir.

## Postgres

Bu adımlar için Docker Desktop açık olmalıdır.

Lokal Postgres başlat:

```bash
make db-up
```

Şemayı oluştur:

```bash
export DATABASE_URL="postgresql://news:news@localhost:54329/news"
make init-db
```

Pipeline'ı Postgres'e yazdır:

```bash
export DATABASE_URL="postgresql://news:news@localhost:54329/news"
make run-db
```

Kayıtları kontrol et:

```bash
psql "$DATABASE_URL" -c "select id, payload #>> '{analysis,category}' as category, payload #>> '{article,title}' as title from news_documents order by id desc limit 10;"
```

## JSONB Payload Örneği

```json
{
  "schema_version": "news-item-v1",
  "source": {
    "key": "bbc_turkce",
    "name": "BBC Türkçe",
    "crawl_url": "https://www.bbc.com/turkce"
  },
  "article": {
    "title": "Başlık",
    "url": "https://example.com/news",
    "summary": "HTML meta açıklaması veya kısa açıklama",
    "published_at": "2026-06-18T10:00:00Z",
    "content_text": "Opsiyonel HTML içerik"
  },
  "analysis": {
    "category": "siyaset",
    "subcategory": "seçim",
    "sentiment": "neutral",
    "summary": "LLM tarafından kısa özet",
    "keywords": ["seçim", "meclis"],
    "confidence": 0.74,
    "analyzer": "openai"
  },
  "pipeline": {
    "collected_at": "2026-06-18T14:00:00Z",
    "content_hash": "..."
  }
}
```

## Test

```bash
make test
```

## Hocaya Anlatılacak Kısa Özet

Bu taslakta haber kaynaklarını normalize etmeye çalışmıyorum. Çünkü haber sitelerinin alanları değişebilir. Bunun yerine her haberi tek `payload jsonb` içinde saklıyorum. Böylece LLM çıktısına yeni alan eklemek veya kaynak bazlı farklı metadata tutmak için migration gerekmiyor. Sadece indekslenmesi gereken alanlar için expression index eklenebilir.

## Geliştirilecek Yerler

- Robots.txt ve site kullanım şartları kaynak bazında kontrol edilmeli.
- HTML extraction site bazlı selectorlarla güçlendirilmeli.
- Aynı haberin farklı kaynaklarda duplicate detection'ı yapılmalı.
- LLM çıktısı için strict schema validation eklenmeli.
- Kategori seti mentorla netleştirilmeli.
- Scheduled run için cron, Airflow veya AWS EventBridge eklenebilir.
