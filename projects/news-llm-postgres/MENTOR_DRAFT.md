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
| Dashboard | Karar özeti, outlier ekranı, etki analizi, drilldown ve kaynak sağlığı olan daha sade tek HTML dashboard ekledim |
| Ekonomi/siyaset etki analizi | TL, ekonomik büyüme, enflasyon, faiz baskısı ve piyasa güveni için -5/+5 skorlayan ilk katmanı ekledim |
| Google Trends benzeri trend | Zamana göre kategori/topic/sinyal yoğunluğunu 0-100 trend index mantığıyla dashboard'a ekledim |
| Büyük kırılım yorumu | Öne çıkan trend veya yüksek etki haberleri için 2-3 cümlelik kısa analiz saklanıyor |
| Yüzeysel haberleri ayırma | Kadir İnanır örneği gibi magazin/kültür ağırlıklı haberleri makro etki hesabına almıyorum |
| Genelden özele akış | İlk ekranda karar özeti, sonra outlier, sonra drilldown mantığına çevirdim |
| Tekil haberleri azaltma | Tekil haberleri ana ekran yerine sadece kanıt/evidence olarak gösteriyorum |
| Server deploy hazırlığı | Mevcut servisleri bozmamak için preflight kontrolü, uvicorn + Apache reverse proxy, deploy doğrulama/proof, refresh script'i ve DNS notları ekledim |
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

Dashboard tarafında tek HTML dosyası üretiyorum. Son güncellemede ekranı kalabalıktan uzaklaştırıp genelden özele giden bir akışa çevirdim. İlk ekran artık tekil haber listesi değil; karar etiketi, ana odak, temel KPI'lar ve drilldown sırasını gösteriyor. Sonra outlier ekranında çok kaynaklı clusterlar, trend kırılımları ve güçlü gösterge sinyalleri öne çıkıyor. Tekil haberleri ana karar noktası yapmıyorum; sadece bu outlierların kanıtı olarak gösteriyorum.

Son güncellemede ekonomi/siyaset haberleri için ayrı bir etki analizi katmanı ekledim. Haber makro analiz için uygunsa TL, ekonomik büyüme, enflasyon, faiz baskısı ve piyasa güveni göstergelerine -5 ile +5 arasında skor veriyor. Magazin, spor, kategori sayfası veya Kadir İnanır örneği gibi makro göstergeyle zayıf ilişkili haberleri hesap dışı bırakıyor; bunu da payload içinde nedeniyle saklıyor.

Trend tarafında Google Trends'e benzer şekilde kategori, topic ve sinyal yoğunluğunu günlük bucket'larda 0-100 index mantığıyla gösteriyorum. Büyük kırılım gördüğü yerlerde de kısa analiz metni saklıyor. API key varsa bu kısa kırılım analizini OpenAI ile zenginleştirecek yol var; key yoksa aynı alan fallback kurallarla doluyor.

Hocanın gönderdiği İstanbul cafe analiz projesine de baktım. Orada hoşuma giden taraf, her görselin bir karar filtresi olarak düşünülmesiydi: önce genel pazar, sonra fırsat, sonra karar matrisi. Bunu bizim projeye şöyle çevirdim: önce genel karar özeti, sonra sadece outlier gündemler, sonra gerektiğinde drilldown. Böylece dashboard her şeyi aynı anda göstermeye çalışmıyor.

Server deploy tarafını da biraz daha dikkatli hale getirdim. Serverda Apache zaten olduğu için dashboard'u doğrudan dışarı açmak yerine küçük bir `uvicorn` servisi olarak `127.0.0.1:8011` üstünde çalıştıracak yapı ekledim. Apache tarafında sadece yeni bir reverse proxy path'i ekleniyor. Böylece mevcut vhostlar, Docker containerları ve servis portları ezilmiyor. Deploy sonrası health/index kontrolü ve proof JSON üretimi de var. Güncel kalması için `server-refresh` ve cron/systemd örneklerini ekledim. DNS verilirse domain'i bu Apache proxy yapısına bağlayabiliriz. Notları `DEPLOY_SERVER.md` içine koydum.

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

Bunları görebilmek için de tek dosyalık bir dashboard ekledim. Son önerilerinizden sonra dashboard'u biraz sadeleştirdim. Artık ilk ekran karar özeti gibi çalışıyor; sonra outlier gündemlere, oradan da drilldown'a gidiliyor. Tekil haberleri ana ekranda kalabalık yapacak şekilde göstermiyorum, sadece outlierları açıklayan kanıt olarak bıraktım.

Son konuştuğumuz ekonomi/siyaset etki analizi tarafını da ekledim. Ayrı bir Etki ekranı var. Burada TL, ekonomik büyüme, enflasyon, faiz baskısı ve piyasa güveni için -5/+5 skorlar görünüyor. Ayrıca Google Trends gibi topic/sinyal yoğunluğu, büyük kırılımlar için kısa yorumlar ve hesap dışı bırakılan yüzeysel haberler de ayrı görünüyor. Örneğin Kadir İnanır gibi magazin/kültür ağırlıklı haberleri makro etki hesabına almıyorum.

Server deploy için de daha güvenli bir akış ekledim. Önce serverdaki port/container/servis durumunu kontrol eden preflight var. Apache hazır olduğu için dashboard'u küçük bir uvicorn servisi olarak localhost'ta ayağa kaldırıp Apache arkasına proxy ediyorum. Deploy sonrası health/index kontrolünün yanına canlı `/ready` ve `/proof` endpointlerini de ekledim. `/proof` içinde deploy modu, public URL, local bind, dashboard dosya durumu ve servis başlangıç zamanı görünüyor. Ayrıca dashboard'un belli aralıklarla güncellenmesi için refresh script'i ve cron/systemd örnekleri var. DNS verilirse aynı Apache proxy yapısına bağlayabiliriz. Böylece serverdaki diğer servislere dokunmadan ilerleyebiliriz.

Bitmiş ürün değil, beraber güncellemek için ilk iskelet.
```
