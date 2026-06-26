# News LLM Postgres Draft

Bu klasör haber toplama işi için ilk taslak. Bitmiş bir uygulama değil; hocayla üzerinden konuşup güncellemek için hazırladım.

Şimdilik yaptığı şey:

- Türkiye merkezli 12 haber kaynağını, Reddit r/Turkey ve Twitter/X denemesini config dosyasından okuyor.
- Normal web sayfasından haber linklerini buluyor.
- Haber sayfasına girip başlık, açıklama, tarih ve paragraf metni çekmeye çalışıyor.
- LLM varsa kategori, özet, keyword, sentiment, entity, lokasyon, olay tipi, önem ve risk/pattern sinyalleri çıkaracak yapı var.
- Benzer haberleri basit metin benzerliğiyle cluster'a ayırıyor.
- Çalıştırma sonunda ayrıca pattern raporu üretiyor.
- Pattern ve cluster sonuçlarını tek HTML dashboard olarak gösteriyor.
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
HTML / Reddit / Twitter source collector
        |
        v
Article page fetch + text extraction
        |
        v
RawNewsItem
        |
        v
LLM analyzer + detailed tags
        |
        v
Clustering + pattern report
        |
        v
Dashboard HTML
        |
        v
JSONB payload
        |
        v
Postgres news_documents(payload jsonb)
```

## Kaynaklar

Başlangıç config'i Türkiye merkezli 12 haber kaynağı, 1 Reddit kaynağı ve 1 Twitter/X denemesi içerir:

- Habertürk
- TRT Haber
- Anadolu Ajansı
- NTV
- Hürriyet
- Milliyet
- Sabah
- Cumhuriyet
- Sözcü
- Bloomberg HT
- Mynet Haber
- Ensonhaber
- Reddit r/Turkey
- Twitter/X Türkiye gündemi

İlk listede BBC Türkçe, Euronews Türkçe ve DW Türkçe gibi Türkçe yayın yapan ama Türkiye merkezli olmayan kaynaklar da vardı. Mentor notundan sonra ana deneme listesi Türkiye'deki haber sitelerine çevrildi.

Bazı haber siteleri Cloudflare, header uyumsuzluğu veya bot koruması kullanabilir. Pipeline kaynak bazında hata yakalar ve diğer kaynaklarla devam eder. Sözcü'de `HEAD` isteği Cloudflare challenge döndürdü ama normal `GET` isteği tarayıcı User-Agent ile HTML verdi. Reddit tarafında `www.reddit.com` modern/JS ağırlıklı, `.json` endpoint 403 döndü; `old.reddit.com/r/Turkey/` ise Selenium kullanmadan HTML verdi.

Twitter/X tarafı normal haber sitesi gibi HTML vermiyor. Public HTML denemesinde post metni gelmediği için pipeline bunu kaynak bazında hata olarak raporluyor. `X_BEARER_TOKEN` verilirse resmi X API recent search endpoint'i deneniyor. Son dry-run'da 14 kaynak config'teydi, 24 payload oluştu ve 5 cluster bulundu. Reddit 403 verdi, Twitter/X için token/public HTML kaynaklı hata raporlandı; diğer kaynaklar devam etti.

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
outputs/latest_patterns.json
```

Dashboard üret:

```bash
make dashboard
```

Çıktı:

```text
outputs/dashboard.html
```

## Dashboard

Dashboard tek dosyalık HTML olarak üretilir. İçinde şu ekranlar var:

- Genel özet: haber, cluster, kategori ve kaynak sayısı
- Kümeler: benzer haber grupları, kaynaklar, ortak terimler ve linkler
- Kategoriler: kategori, olay tipi, topic ve risk sinyali dağılımları
- Harita: lokasyon sayımları ve harita benzeri görünüm
- Kaynaklar: kaynak dağılımı ve Twitter/Reddit gibi hata veren kaynaklar

## OpenAI ile Çalıştırma

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
make dry-run-llm
```

API key yoksa pipeline otomatik olarak fallback analyzer kullanabilir.

## Twitter/X ile Deneme

Twitter/X public HTML çoğu zaman JS/login duvarı nedeniyle post metnini vermiyor. Resmi API ile denemek için token env üzerinden verilir:

```bash
export X_BEARER_TOKEN="..."
make dry-run
```

Token yoksa pipeline Twitter/X kaynağını denemeye çalışır, post metni çıkaramazsa hatayı summary içinde gösterir ve diğer kaynaklarla devam eder.

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
    "key": "haberturk",
    "name": "Habertürk",
    "crawl_url": "https://www.haberturk.com"
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
    "topics": ["siyaset", "policy_decision", "seçim"],
    "entities": {
      "persons": [],
      "organizations": ["TBMM"],
      "locations": ["Ankara"]
    },
    "event_type": "policy_decision",
    "geography": ["Ankara"],
    "importance": "high",
    "risk_flags": ["political_tension"],
    "confidence": 0.74,
    "analyzer": "openai"
  },
  "cluster": {
    "cluster_id": "cluster_...",
    "cluster_size": 2,
    "method": "token_cosine_v1",
    "representative_title": "Başlık",
    "common_terms": ["seçim", "meclis"],
    "related_urls": ["https://example.com/related"]
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

Bu taslakta haber kaynaklarını tamamen tek formata zorlamıyorum. Çünkü haber sitelerinin alanları değişebilir. Bunun yerine her haberi tek `payload jsonb` içinde saklıyorum. Böylece LLM çıktısına entity, olay tipi, önem, risk sinyali veya cluster gibi yeni alanlar eklemek için migration gerekmiyor. Sadece indekslenmesi gereken alanlar için expression index eklenebilir.

## Geliştirilecek Yerler

- Robots.txt ve site kullanım şartları kaynak bazında kontrol edilmeli.
- HTML extraction site bazlı selectorlarla güçlendirilmeli.
- Aynı haberin farklı kaynaklarda duplicate detection'ı yapılmalı.
- Twitter/X için resmi API token veya kontrollü browser session akışı netleştirilmeli.
- Clustering tarafı ileride TF-IDF/embedding + KMeans, DBSCAN veya HDBSCAN ile güçlendirilebilir.
- LLM çıktısı için strict schema validation eklenmeli.
- Kategori seti mentorla netleştirilmeli.
- Scheduled run için cron, Airflow veya AWS EventBridge eklenebilir.
