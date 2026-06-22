# Kısa Taslak Notu

Bu klasör, haber toplama işi için hazırladığım ilk taslak. Bitmiş bir uygulama değil. Daha çok "mantık doğru mu, buradan nasıl devam edelim?" diye konuşmak için hazırladım.

## İstenen Şeylere Karşılık Ne Var?

| İstenen | Şu an ne yaptım? |
|---|---|
| 5-10 haber sitesi | `config/sources.json` içine Türkiye merkezli 12 haber kaynağı ve 1 Reddit kaynağı ekledim |
| Haber toplama | Normal web sayfasından haber linklerini bulup haber sayfasına giriyorum |
| LLM analizi | `llm.py` içinde OpenAI ile analiz edecek yapı var |
| Siyaset, ekonomi vb. ayırma | Kategori listesi var: siyaset, ekonomi, dünya, teknoloji, spor, sağlık, kültür, hukuk, eğitim, diğer |
| Postgres'e JSONB kaydetme | `news_documents` tablosunda tek `payload jsonb` alanı var |
| Yapı değişebilir | Yeni alanlar tabloyu değiştirmeden `payload` içine eklenebilir |

## Şu An Nasıl Çalışıyor?

```bash
cd /Users/omer/aws-analytics-pipeline/projects/news-llm-postgres
source /Users/omer/aws-analytics-pipeline/.venv/bin/activate
make dry-run
```

Kaynak listesi şu an Türkiye'deki haber sitelerine göre güncellendi: Habertürk, TRT Haber, Anadolu Ajansı, NTV, Hürriyet, Milliyet, Sabah, Cumhuriyet, Sözcü, Bloomberg HT, Mynet Haber, Ensonhaber.

Sözcü için kontrol ettim: `HEAD` isteği Cloudflare challenge/403 döndürdü ama normal `GET` isteği tarayıcı User-Agent ile HTML verdi. Yani tamamen kapalı değil; crawler tarafında doğru header ile linkler ve haber detayları alınabiliyor.

Reddit için de denedim. `www.reddit.com` modern/JS ağırlıklı geldi, `.json` endpoint 403 döndü. Selenium kullanmadan `old.reddit.com/r/Turkey/` üzerinden daha temiz HTML alabildim. Sticky postları atlayıp normal postların comments sayfasına gidiyorum; başlık, post metni ve ilk yorumlardan örnek metin çekiliyor.

Son dry-run sonucunda Reddit dahil 13 kaynak config'te vardı. Toplam 26 payload oluştu ve hata dönmedi. Reddit r/Turkey'den 2 post geldi. Çıktı dosyası:

```text
outputs/latest_payloads.jsonl
```

## LLM ile Deneme

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
make dry-run-llm
```

API key yoksa basit bir fallback analyzer çalışıyor. Bu sadece akışı test etmek için var. Asıl analiz LLM ile yapılacak.

## Postgres Tarafı

Tablo yapısı basit:

```sql
CREATE TABLE IF NOT EXISTS news_documents (
    id BIGSERIAL PRIMARY KEY,
    content_hash TEXT NOT NULL UNIQUE,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload JSONB NOT NULL
);
```

Docker Desktop açıkken denemek için:

```bash
make db-up
export DATABASE_URL="postgresql://news:news@localhost:54329/news"
make init-db
make run-db
```

## Neden JSONB Kullandım?

Haberden çıkaracağımız alanlar zamanla değişebilir. İlk başta kategori, özet ve keyword yeterli olabilir. Sonra kişi, kurum, lokasyon, önem skoru veya benzer haberler gibi alanlar eklenebilir.

Bunları her seferinde ayrı kolon yapmak yerine tek `payload jsonb` içinde tutmak daha esnek. Çok sorgulanacak alanlar için sonradan index eklenebilir.

## Şu An Eksik Olanlar

- Docker Desktop kapalı olduğu için Postgres'e canlı yazma adımını henüz lokal doğrulamadım.
- OpenAI API key ile gerçek LLM çıktısını henüz denemedim.
- HTML yapıları siteye göre değiştiği için haber metni çekme kısmı kaynak bazında iyileştirilecek.
- Anadolu Ajansı için ayrı header/parser ayarı gerekiyor.
- Kaynakların robots.txt ve kullanım şartlarına ayrıca bakmak lazım.
- Kategori listesi hocayla netleşince güncellenecek.

## Hocaya Atılacak Kısa Mesaj

```text
Hocam haber toplama işi için ilk taslağı hazırladım.

Şu an Türkiye'deki haber kaynaklarını config'e aldım: Habertürk, TRT Haber, Anadolu Ajansı, NTV, Hürriyet, Milliyet, Sabah, Cumhuriyet, Sözcü, Bloomberg HT, Mynet Haber, Ensonhaber. Reddit için de r/Turkey'i old.reddit üzerinden denedim. Normal web sayfasından linkleri bulup detay sayfasına girmeye çalışıyorum. LLM tarafında kategori, özet, keyword ve sentiment çıkaracak yapı var. Sonucu Postgres'te tek payload jsonb alanında tutacak şekilde yazdım; çünkü ileride çıkaracağımız alanlar değişebilir.

Bitmiş ürün değil, beraber güncellemek için ilk iskelet.
```
