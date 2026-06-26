# Kısa Taslak Notu

Bu klasör, haber toplama işi için hazırladığım ilk taslak. Bitmiş bir uygulama değil. Daha çok "mantık doğru mu, buradan nasıl devam edelim?" diye konuşmak için hazırladım.

## İstenen Şeylere Karşılık Ne Var?

| İstenen | Şu an ne yaptım? |
|---|---|
| 5-10 haber sitesi | `config/sources.json` içine Türkiye merkezli 12 haber kaynağı, 1 Reddit kaynağı ve 1 Twitter/X denemesi ekledim |
| Haber toplama | Normal web sayfasından haber linklerini bulup haber sayfasına giriyorum |
| LLM analizi | `llm.py` içinde OpenAI ile analiz edecek yapı var |
| Siyaset, ekonomi vb. ayırma | Kategori listesi var: siyaset, ekonomi, dünya, teknoloji, spor, sağlık, kültür, hukuk, eğitim, diğer |
| Kapsamlı etiketleme | Kategoriye ek olarak olay tipi, konu başlıkları, kişi/kurum/yer, lokasyon, önem ve risk/pattern sinyalleri ekledim |
| Haberlerde pattern bulma | Benzer haberleri basit metin benzerliğiyle cluster'a ayıran ve genel pattern raporu çıkaran yapı ekledim |
| Dashboard | Insight kartları, cluster önem skoru, entity/topic ağı, filtreli haber tablosu, harita/lokasyon ve kaynak sağlığı ekranları olan tek HTML dashboard ekledim |
| Twitter/X denemesi | Public HTML ve resmi API token yolunu ayırdım; token yoksa neden alınamadığını kaynak hatası olarak raporluyor |
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

Twitter/X için de ilk denemeyi ekledim. Public HTML tarafında post metni server-render gelmediği için normal scraping ile alınamadı. Kodda iki yol bıraktım: `X_BEARER_TOKEN` varsa resmi X API recent search deneniyor, token yoksa public HTML denenip hata raporlanıyor. Bu şekilde Twitter kaynağının neden zor olduğunu da çıktıda görebiliyoruz.

Son dry-run doğrulamasında Twitter dahil 14 kaynak config'te vardı. Canlı kaynaklara göre payload ve cluster sayısı değişebiliyor. Reddit, Twitter/X veya bazı haber kaynakları zaman zaman erişim hatası verebiliyor; pipeline bunları kaynak hatası olarak yazıp diğer kaynaklarla devam ediyor. Çıktı dosyaları:

```text
outputs/latest_payloads.jsonl
outputs/latest_patterns.json
outputs/dashboard.html
```

Temel kategoriye ek olarak daha kapsamlı etiketleme de ekledim. Şu an her haber için kabaca şu alanlar çıkıyor:

- `category`: ana kategori
- `event_type`: olay tipi
- `topics`: konu başlıkları
- `entities`: kişi, kurum ve yer bilgileri
- `geography`: haberin geçtiği yerler
- `importance`: önem seviyesi
- `risk_flags`: pattern ararken kullanılacak sinyaller

Clustering tarafında ilk sürüm basit metin benzerliğiyle çalışıyor. Aynı olayı anlatan haberler benzer kelimeler, başlıklar ve topic'ler üzerinden aynı cluster'a düşüyor. Bunu özellikle ilk taslakta anlaşılır tutmak istedim; sonraki adımda embedding tabanlı benzerlik veya KMeans/DBSCAN/HDBSCAN gibi yöntemlerle daha düzgün hale getirilebilir.

Dashboard tarafında tek HTML dosyası üretiyorum. İçinde genel özet, otomatik insight kartları, öncelikli clusterlar, cluster önem skoru, kategori dağılımı, topic/risk sinyalleri, entity/topic ağı, filtreli haber tablosu, lokasyon haritası ve kaynak sağlığı ekranı var. Böylece işi sadece kod olarak değil, bakılabilecek küçük bir ürün ekranı gibi gösterebiliyoruz.

## LLM ile Deneme

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
make dry-run-llm
```

API key yoksa basit bir fallback analyzer çalışıyor. Bu sadece akışı test etmek için var. Asıl detaylı analiz LLM ile yapılacak.

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

Haberden çıkaracağımız alanlar zamanla değişebilir. İlk başta kategori, özet ve keyword yeterli olabilir. Sonra kişi, kurum, lokasyon, önem skoru, risk sinyali veya benzer haber cluster'ı gibi alanlar eklenebilir.

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

Şu an Türkiye'deki haber kaynaklarını config'e aldım: Habertürk, TRT Haber, Anadolu Ajansı, NTV, Hürriyet, Milliyet, Sabah, Cumhuriyet, Sözcü, Bloomberg HT, Mynet Haber, Ensonhaber. Reddit için de r/Turkey'i old.reddit üzerinden denedim. Twitter/X tarafında da public HTML ve resmi API token yolunu ayırdım. Token olmadığı durumda public HTML post metni vermediği için kaynak hatası olarak raporluyor. Normal web sayfasından linkleri bulup detay sayfasına girmeye çalışıyorum.

Etiketleme tarafını da sadece kategori seviyesinde bırakmadım. Kategoriye ek olarak olay tipi, konu başlıkları, kişi/kurum/yer, lokasyon, önem seviyesi ve risk/pattern sinyalleri çıkacak şekilde genişlettim. Benzer haberleri de basit metin benzerliğiyle cluster'a ayıran ilk yapıyı ekledim. Çıktıları Postgres'te tek payload jsonb alanında tutuyorum; çünkü ileride bu alanlar değişebilir.

Bunları görebilmek için de tek dosyalık bir dashboard ekledim. Genel özet, insight kartları, cluster önem skoru, entity/topic ağı, kategori dağılımı, filtreli haber tablosu, lokasyon/harita ve kaynak sağlığı ekranları var.

Bitmiş ürün değil, beraber güncellemek için ilk iskelet.
```
