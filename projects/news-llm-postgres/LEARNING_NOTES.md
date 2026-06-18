# Ne Yaptık, Neden Yaptık?

Bu not, projeyi ezberlemek için değil, ne kurduğumuzu gerçekten anlamak için yazıldı.

## 1. Problemi Parçalara Ayırdık

Hocanın isteği aslında birkaç küçük işten oluşuyor:

1. Haber kaynakları bul.
2. Bu kaynaklardan haberleri topla.
3. Gelen metni LLM'e analiz ettir.
4. Haberi türüne göre ayır: siyaset, ekonomi, spor vb.
5. Sonucu Postgres'e kaydet.
6. Şema değişebileceği için veriyi tek `jsonb` alanda tut.

Biz de projeyi bu parçalara göre böldük.

## 2. Neden RSS ile Başladık?

Haber sitelerinden veri toplamanın iki yolu var:

- HTML scraping: Sayfanın içinden başlık, açıklama, metin çekmek.
- RSS feed: Haber sitesinin zaten verdiği makine-okunabilir haber akışını kullanmak.

İlk taslak için RSS daha doğru çünkü:

- Daha stabildir.
- Daha az kırılır.
- Başlık, link, özet ve tarih genelde hazır gelir.
- 5-10 kaynakla hızlıca çalışan demo çıkarmayı sağlar.

Bu yüzden kaynakları [config/sources.json](config/sources.json) içinde tuttuk.

## 3. Kaynakları Neden Config Dosyasına Koyduk?

Kaynaklar kodun içine gömülü olsaydı yeni site eklemek için kod değiştirmek gerekirdi.

Biz şöyle yaptık:

```json
{
  "key": "bbc_turkce",
  "name": "BBC Türkçe",
  "feed_url": "https://feeds.bbci.co.uk/turkce/rss.xml",
  "enabled": true
}
```

Böylece yeni haber sitesi eklemek için sadece config'e yeni kayıt eklemek yeterli.

## 4. Pipeline Mantığı

Basit akış şu:

```text
sources.json
    -> RSS fetch
    -> RawNewsItem
    -> LLM / fallback analyzer
    -> JSON payload
    -> JSONL file veya Postgres JSONB
```

Kodda bunun ana yeri:

- [src/news_pipeline/fetchers.py](src/news_pipeline/fetchers.py): Haberleri toplar.
- [src/news_pipeline/llm.py](src/news_pipeline/llm.py): Haberi analiz eder.
- [src/news_pipeline/pipeline.py](src/news_pipeline/pipeline.py): Tüm akışı birleştirir.
- [src/news_pipeline/storage.py](src/news_pipeline/storage.py): Postgres'e yazar.

## 5. LLM Katmanını Nasıl Kurduk?

İki analyzer var:

1. `OpenAIAnalyzer`
   - `OPENAI_API_KEY` varsa gerçek LLM çağırır.
   - Kategori, özet, sentiment, keyword, confidence üretir.

2. `RuleBasedAnalyzer`
   - API key yoksa demo bozulmasın diye basit keyword kurallarıyla çalışır.
   - Mesela haberde `faiz`, `dolar`, `enflasyon` geçiyorsa kategori `ekonomi` olabilir.

Bu fallback profesyonel çözüm değil. Sadece geliştirme sırasında pipeline'ın uçtan uca çalışmasını sağlar.

## 6. Neden JSONB?

Hocanın söylediği önemli yer burası:

> structure değişecek çünkü

Normal tablo yapsaydık şöyle kolonlar açardık:

```sql
title text,
url text,
category text,
summary text,
sentiment text
```

Ama yarın LLM çıktısına şunlar eklenebilir:

- kişiler
- kurumlar
- şehirler
- önem skoru
- haberin risk seviyesi
- benzer haberler
- kaynak güven skoru

Her yeni alan için tablo migration yapmak yerine tek bir esnek alan kullandık:

```sql
payload jsonb
```

Bu sayede tüm haber dokümanı şöyle saklanıyor:

```json
{
  "source": {},
  "article": {},
  "analysis": {},
  "pipeline": {}
}
```

Yani veri yapısı değişirse payload içine yeni alan eklenir.

## 7. Peki JSONB Kullanmanın Dezavantajı Ne?

JSONB esnektir ama her şeyi çözen sihirli çözüm değildir.

Dezavantajlar:

- Çok fazla sorgu yapılacak alanlar için index gerekir.
- Veri doğrulaması uygulama tarafında daha önemli hale gelir.
- Her şeyi JSONB'ye atarsan raporlama karmaşıklaşabilir.

Bu yüzden taslakta bazı expression index'ler ekledik:

```sql
CREATE INDEX idx_news_documents_category
    ON news_documents ((payload #>> '{analysis,category}'));
```

Bu index kategoriye göre sorguyu hızlandırır.

## 8. Content Hash Neden Var?

Aynı haber tekrar gelirse duplicate kayıt oluşmasın diye `content_hash` üretiyoruz.

Basit mantık:

```text
source_key + url -> sha256 hash
```

Bu hash unique olduğu için aynı haber tekrar gelirse insert yerine update yapılır.

## 9. Neyi Test Ettik?

Şunları test ettik:

- Rule-based analyzer ekonomi haberini doğru sınıflıyor mu?
- JSON payload beklenen alanlarla oluşuyor mu?
- Content hash stabil mi?

Komut:

```bash
make test
```

Sonuç:

```text
Ran 3 tests
OK
```

## 10. Şu An Ne Çalıştı?

Dry-run çalıştı:

```bash
make dry-run
```

Son denemede:

- 9 haber kaynağı config'te vardı.
- 14 haber payload'ı üretildi.
- Çıktı `outputs/latest_payloads.jsonl` dosyasına yazıldı.

Bu Postgres'e yazmadan önce pipeline'ın haber toplama ve analiz kısmının çalıştığını gösterir.

## 11. Henüz Ne Eksik?

- Docker Desktop kapalı olduğu için Postgres yazma adımı canlı doğrulanmadı.
- OpenAI API key ile gerçek LLM analizi henüz denenmedi.
- HTML article body extraction başlangıç seviyesinde.
- Kaynakların robots.txt ve kullanım şartları kontrol edilmeli.
- Kategoriler hocayla netleşince güncellenmeli.

## 12. Hocaya Nasıl Anlatılır?

Kısa ve doğru anlatım:

```text
Hocam ilk taslakta haber kaynaklarını config dosyasına aldım. RSS üzerinden haberleri topluyorum. LLM katmanında kategori, özet, keyword ve sentiment üretilecek şekilde yapı kurdum. API key yokken pipeline bozulmasın diye fallback analyzer var. Sonucu Postgres'te tek payload jsonb alanına yazacak şekilde tasarladım, çünkü LLM çıktısının yapısı zamanla değişebilir.
```

## 13. Sonraki Mantıklı Adım

Sıradaki güncelleme şu olmalı:

1. Docker Desktop açıp Postgres yazmayı doğrula.
2. OpenAI API key ile `make dry-run-llm` çalıştır.
3. 2-3 haber için LLM çıktısının kaliteli olup olmadığına bak.
4. Kategori listesini hocayla netleştir.
5. JSONB içinden kategori/tarih/kaynak bazlı örnek SQL sorguları ekle.
