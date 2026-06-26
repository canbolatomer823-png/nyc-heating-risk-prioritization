# Ne Yaptık?

Bu notu kendim öğrenmek için yazdım. Projenin amacı hocanın söylediği işi küçük parçalara bölüp çalışan bir başlangıç çıkarmak.

## 1. İşi Parçaladık

İstek şuydu:

- 5-10 haber sitesi bul.
- Haberleri topla.
- İçeriği LLM ile analiz et.
- Haberi türüne göre ayır.
- Postgres'e kaydet.
- Yapı değişeceği için tek `jsonb` alan kullan.

Ben de kodu buna göre ayırdım:

```text
kaynaklar -> haber çekme -> analiz -> clustering/pattern -> payload oluşturma -> Postgres'e yazma
```

## 2. Neden Normal Web Crawling'e Çevirdik?

İlk akılda RSS ile yapmak daha kolaydı ama hocanın dediği doğru: gerçek hayatta her veri RSS gibi temiz gelmiyor.

Bu yüzden akışı normal web crawling'e çevirdim:

- Önce haber sitesinin ana/liste sayfasına gidiyor.
- Sayfadaki linkleri geziyor.
- Haber linkine benzeyenleri seçiyor.
- Her haber sayfasına girip başlık, açıklama, tarih ve paragraf metni çıkarmaya çalışıyor.

Bu RSS'e göre daha zor ama hocanın istediği probleme daha yakın.

Kaynaklar burada:

[config/sources.json](config/sources.json)

İlk listede BBC Türkçe, Euronews Türkçe ve DW Türkçe de vardı. Onlar Türkçe yayın yapıyor ama Türkiye merkezli kaynaklar değil. Hocanın "Türkiye'deki haber sitelerini dene" notundan sonra listeyi Türkiye merkezli sitelere çevirdim:

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

## 3. Kaynakları Neden Config'e Koyduk?

Kaynakları kodun içine yazsaydım yeni site eklemek için Python dosyası değiştirmek gerekecekti.

Onun yerine şöyle bir yapı yaptım:

```json
{
  "key": "haberturk",
  "name": "Habertürk",
  "crawl_url": "https://www.haberturk.com",
  "allowed_domains": ["haberturk.com"],
  "enabled": true
}
```

Yeni site eklemek için config'e yeni kayıt eklemek yeterli.

## 4. Kodda Hangi Dosya Ne İş Yapıyor?

- [src/news_pipeline/fetchers.py](src/news_pipeline/fetchers.py): Liste sayfasından linkleri bulur, haber sayfasından metin çeker.
- [src/news_pipeline/llm.py](src/news_pipeline/llm.py): Haberi analiz eder.
- [src/news_pipeline/clustering.py](src/news_pipeline/clustering.py): Benzer haberleri cluster'a ayırır ve pattern raporu çıkarır.
- [src/news_pipeline/dashboard.py](src/news_pipeline/dashboard.py): Payload ve pattern çıktılarından dashboard HTML'i üretir.
- [src/news_pipeline/pipeline.py](src/news_pipeline/pipeline.py): Bütün akışı sırayla çalıştırır.
- [src/news_pipeline/storage.py](src/news_pipeline/storage.py): Postgres'e yazar.
- [src/news_pipeline/cli.py](src/news_pipeline/cli.py): Terminalden komut çalıştırmayı sağlar.

## 5. LLM Kısmı Nasıl Çalışıyor?

İki yol var:

1. `OpenAIAnalyzer`
   - `OPENAI_API_KEY` varsa LLM'e gider.
   - Kategori, özet, sentiment, keyword ve confidence üretir.
   - Yeni sürümde olay tipi, konu başlıkları, kişi/kurum/yer, lokasyon, önem seviyesi ve risk/pattern sinyalleri de bekleniyor.

2. `RuleBasedAnalyzer`
   - API key yokken akış bozulmasın diye var.
   - Basit kelime kurallarıyla kategori tahmin eder.
   - Mesela `faiz`, `dolar`, `enflasyon` geçerse ekonomi diyebilir.
   - Ayrıca basit şekilde olay tipi, lokasyon ve risk sinyali çıkarmaya çalışır.

Fallback analyzer gerçek çözüm değil. Sadece "pipeline baştan sona çalışıyor mu?" diye bakmak için var.

## 6. Kapsamlı Etiketleme Ne Demek?

Temel etiketleme şöyleydi:

```json
{
  "category": "ekonomi",
  "summary": "Kısa özet",
  "keywords": ["faiz", "dolar"]
}
```

Kapsamlı etiketleme ise habere biraz daha analitik bakmak demek:

```json
{
  "category": "ekonomi",
  "event_type": "market_update",
  "topics": ["ekonomi", "faiz", "merkez bankası"],
  "entities": {
    "persons": [],
    "organizations": ["Merkez Bankası"],
    "locations": ["Türkiye"]
  },
  "geography": ["Türkiye"],
  "importance": "high",
  "risk_flags": ["market_pressure"]
}
```

Yani sadece "bu haber ekonomi" demiyoruz. Aynı zamanda "hangi olay tipi, hangi kurumlar, hangi yerler, önemi ne, hangi pattern sinyalleri var?" diye bakıyoruz.

## 7. Clustering ve Pattern Bulma Nedir?

Clustering, etiketi önceden vermeden benzer kayıtları gruplamak demek.

Haber örneğinde mantık şu:

```text
Habertürk: Merkez Bankası faiz kararını açıkladı
NTV: Merkez Bankası faiz kararını duyurdu
Bloomberg HT: Faiz kararı sonrası piyasalarda hareketlilik
```

Bu üç haber farklı kaynaklardan gelebilir ama aynı gündem etrafında olabilir. Clustering ile bunları aynı gruba koymaya çalışıyoruz.

Bu projedeki ilk sürüm basit çalışıyor:

1. Haberin başlık, özet, metin ve keyword alanlarını alıyor.
2. Kelimeleri normalize ediyor.
3. Haberler arası kelime benzerliğine bakıyor.
4. Benzer olanları aynı `cluster_id` altına koyuyor.

Bu henüz ileri seviye ML değil. Öğrenmek için iyi bir başlangıç. Sonraki adımda aynı mantık embedding ile yapılabilir:

- Haber metni embedding'e çevrilir.
- Benzer embedding'ler yakın çıkar.
- KMeans, DBSCAN veya HDBSCAN gibi yöntemlerle kümeler bulunur.

Pattern bulma da clustering'in üstüne kuruluyor:

- Aynı konu farklı kaynaklarda tekrar ediyor mu?
- En sık geçen kategori ne?
- Hangi şehir veya kurumlar öne çıkıyor?
- Hangi risk sinyalleri sıklaşıyor?

Bu bilgiler `outputs/latest_patterns.json` dosyasında özetleniyor.

## 8. Dashboard Neden Ekledik?

Hocanın "ürün gibi bak" demesi önemli. Sadece terminal çıktısı üretmek yeterli değil; çıkan şeyi bir ekranda görebilmek lazım.

Bu yüzden tek dosyalık dashboard ekledim:

```bash
make dashboard
```

Ürettiği dosya:

```text
outputs/dashboard.html
```

Dashboard içinde şu ekranlar var:

- Genel özet
- Otomatik insight kartları
- Öncelikli clusterlar ve cluster etki skoru
- Cluster listesi
- Kategori ve olay tipi dağılımı
- Topic ve risk sinyalleri
- Entity/topic ağı
- Filtreli haber inceleme tablosu
- Lokasyon/harita görünümü
- Kaynak sağlığı, kaynak dağılımı ve kaynak hataları

Bunun amacı şu: "Bu sistem neyi çözüyor?" sorusuna daha ürün gibi cevap vermek. Haberleri topluyor, etiketliyor, benzerlerini grupluyor, hangi gündemin daha önemli göründüğünü skorlayıp tek ekranda inceletiyor.

## 9. Twitter/X Neden Zor?

Twitter/X normal haber sitesi gibi çalışmıyor. Haber sitelerinde çoğu zaman HTML içinde link, başlık ve paragraf bulabiliyoruz. Twitter/X'te ise içerik büyük ölçüde JavaScript, login ve API kuralları üzerinden geliyor.

Bu yüzden iki yol bıraktım:

1. `X_BEARER_TOKEN` varsa resmi X API recent search endpoint'i denenir.
2. Token yoksa public HTML denenir.

Bu çalıştırmada token yoktu. Public HTML de post metnini vermedi. O yüzden pipeline Twitter kaynağı için şu mantıkta hata verdi:

```text
Twitter/X public HTML did not expose post text
```

Bu kötü değil; hocanın "orası baya zor" dediği şeyin teknik sebebini göstermiş oluyor. Diğer kaynaklar çalışmaya devam ediyor. Sonraki adımda ya resmi API token alınır ya da Selenium/browser session ile ayrı bir deneme yapılır.

## 10. JSONB Neden Önemli?

Hocanın söylediği en önemli nokta buydu:

```text
structure değişecek çünkü
```

Yani bugün şöyle bir çıktı olabilir:

```json
{
  "category": "ekonomi",
  "summary": "Kısa özet",
  "keywords": ["faiz", "dolar"]
}
```

Yarın buna şunlar eklenebilir:

- kişi isimleri
- kurumlar
- şehirler
- önem skoru
- haberin tonu
- benzer haberler
- cluster bilgisi
- pattern sinyalleri

Eğer hepsini ayrı kolon yaparsak her değişiklikte tabloyu değiştirmek gerekir. O yüzden tek alan kullandık:

```sql
payload jsonb
```

Payload içinde de kabaca şu bölümler var:

```json
{
  "source": {},
  "article": {},
  "analysis": {},
  "pipeline": {}
}
```

## 11. JSONB'nin Kötü Tarafı Var mı?

Var.

JSONB esnek ama her şeyi JSONB'ye atmak da iyi değil. Çok sık sorgulanacak alanlar için index gerekir.

Bu yüzden örnek olarak kategori index'i ekledim:

```sql
CREATE INDEX idx_news_documents_category
    ON news_documents ((payload #>> '{analysis,category}'));
```

Yani veri esnek kalıyor ama kategoriye göre sorgu da hızlanabiliyor.

## 12. `content_hash` Neden Var?

Aynı haber tekrar gelirse Postgres'e tekrar tekrar eklenmesin diye.

Mantık basit:

```text
kaynak + haber linki -> hash
```

Bu hash unique. Aynı haber tekrar gelirse yeni kayıt açmak yerine mevcut kayıt güncellenir.

## 13. Şu Ana Kadar Ne Çalıştı?

Test:

```bash
make test
```

Sonuç:

```text
Ran 13 tests
OK
```

Dry-run:

```bash
make dry-run
```

Sözcü için ayrıca baktım. `HEAD` isteği Cloudflare challenge/403 döndürdü ama normal `GET` isteği tarayıcı User-Agent ile HTML verdi. Bu yüzden Sözcü tamamen kapalı değil; doğru istek tipi ve header ile crawler'a eklenebilir.

Reddit için de deneme yaptım. Normal `www.reddit.com` sayfası modern/JS ağırlıklı, `.json` endpoint de 403 döndü. `old.reddit.com/r/Turkey/` ise Selenium kullanmadan HTML verdi. Oradan post linklerini alıp comments sayfasına gidince başlık, post metni ve yorumlardan örnek metin çekilebildi.

Twitter/X için deneme yaptım. Resmi API tarafı için `X_BEARER_TOKEN` destekli kod ekledim. Token yoksa public HTML deneniyor. Bu denemede public HTML post metnini vermediği için Twitter kaynağı hata olarak raporlandı ama pipeline diğer kaynaklarla devam etti.

Son crawler denemesinde:

- Twitter dahil 14 kaynak config'te vardı.
- Payload ve cluster sayısı canlı kaynakların o anki durumuna göre değişiyor.
- Reddit, Twitter/X veya bazı haber kaynakları zaman zaman erişim hatası verebiliyor; pipeline diğer kaynaklarla devam ediyor.
- Çıktı `outputs/latest_payloads.jsonl` dosyasına yazıldı.
- Pattern özeti `outputs/latest_patterns.json` dosyasına yazılıyor.
- Dashboard `outputs/dashboard.html` dosyasına yazılıyor.
- Pattern raporunda `insight_cards`, `cluster_rankings`, `source_health`, `entity_network` ve `coverage_matrix` alanları oluşuyor.

## 14. Şu An Eksikler

- Docker Desktop kapalı olduğu için Postgres yazma adımını canlı denemedim.
- OpenAI API key ile gerçek LLM çıktısını henüz denemedim.
- Normal web crawling'e geçti ama her sitenin HTML yapısı farklı olduğu için selector/parser kısmı geliştirilecek.
- Anadolu Ajansı için ayrı header/parser ayarı gerekiyor.
- Twitter/X için resmi API token veya kontrollü Selenium/browser session denemesi gerekiyor.
- Clustering şu an basit kelime benzerliğiyle çalışıyor; embedding tabanlı hale getirilebilir.
- Dashboard şu an tek HTML; ileride FastAPI veya React ekranına çevrilebilir.
- Cluster önem skoru şu an kural bazlı; ileride embedding/LLM skoru ile daha iyi hale getirilebilir.
- Kaynakların kullanım şartlarına bakmak lazım.
- Kategoriler hocayla konuşup netleşmeli.

## 15. Hocaya Nasıl Anlatırım?

Kısa anlatım:

```text
Hocam kaynakları Türkiye'deki haber sitelerine göre güncelledim: Habertürk, TRT Haber, Anadolu Ajansı, NTV, Hürriyet, Milliyet, Sabah, Cumhuriyet, Sözcü, Bloomberg HT, Mynet Haber ve Ensonhaber. Sözcü'de HEAD isteği Cloudflare'a takılıyor ama normal GET isteğiyle HTML alabildim. RSS yerine normal web sayfasından haber linklerini bulup haber sayfasına giren bir crawler akışı kurdum.

Twitter/X tarafını da denedim. Orası normal HTML vermediği için token'sız public scraping tarafı post metnini çıkarmadı. Kodda resmi API token ile çalışacak yolu ekledim; token yoksa hatayı kaynak bazında raporlayıp diğer kaynaklarla devam ediyor.

Etiketleme tarafını da genişlettim. Kategoriye ek olarak olay tipi, konu başlıkları, kişi/kurum/yer, lokasyon, önem seviyesi ve risk/pattern sinyalleri çıkıyor. Benzer haberleri de basit metin benzerliğiyle cluster'a ayıran ilk yapıyı ekledim. Sonucu Postgres'te tek payload jsonb alanında tutuyorum. Böyle yaptım çünkü ileride çıkarılacak alanlar değişirse tabloyu sürekli değiştirmek gerekmeyecek.

Bunları görebilmek için de dashboard ekledim. Genel özet, insight kartları, cluster önem skoru, entity/topic ağı, kategori dağılımı, filtreli haber tablosu, lokasyon/harita ve kaynak sağlığı ekranları var.
```

## 16. Bir Sonraki Adım

Sıradaki iş bence şu:

1. Docker Desktop açıp Postgres yazmayı denemek.
2. OpenAI API key ile `make dry-run-llm` çalıştırmak.
3. LLM'in 2-3 haber için doğru kategori verip vermediğine bakmak.
4. Clustering sonucunda aynı olayların doğru gruplanıp gruplanmadığına bakmak.
5. Dashboard'daki ekranları hocayla konuşup hangi metrikler gerekli netleştirmek.
6. Twitter/X için API token veya Selenium/browser session kararını vermek.
7. Hocayla kategori ve pattern alanlarını netleştirmek.
8. JSONB üzerinden örnek SQL sorguları eklemek.
