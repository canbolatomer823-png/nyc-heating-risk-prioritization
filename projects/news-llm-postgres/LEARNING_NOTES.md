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
kaynaklar -> haber çekme -> analiz -> payload oluşturma -> Postgres'e yazma
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

## 3. Kaynakları Neden Config'e Koyduk?

Kaynakları kodun içine yazsaydım yeni site eklemek için Python dosyası değiştirmek gerekecekti.

Onun yerine şöyle bir yapı yaptım:

```json
{
  "key": "bbc_turkce",
  "name": "BBC Türkçe",
  "crawl_url": "https://www.bbc.com/turkce",
  "allowed_domains": ["bbc.com"],
  "enabled": true
}
```

Yeni site eklemek için config'e yeni kayıt eklemek yeterli.

## 4. Kodda Hangi Dosya Ne İş Yapıyor?

- [src/news_pipeline/fetchers.py](src/news_pipeline/fetchers.py): Liste sayfasından linkleri bulur, haber sayfasından metin çeker.
- [src/news_pipeline/llm.py](src/news_pipeline/llm.py): Haberi analiz eder.
- [src/news_pipeline/pipeline.py](src/news_pipeline/pipeline.py): Bütün akışı sırayla çalıştırır.
- [src/news_pipeline/storage.py](src/news_pipeline/storage.py): Postgres'e yazar.
- [src/news_pipeline/cli.py](src/news_pipeline/cli.py): Terminalden komut çalıştırmayı sağlar.

## 5. LLM Kısmı Nasıl Çalışıyor?

İki yol var:

1. `OpenAIAnalyzer`
   - `OPENAI_API_KEY` varsa LLM'e gider.
   - Kategori, özet, sentiment, keyword ve confidence üretir.

2. `RuleBasedAnalyzer`
   - API key yokken akış bozulmasın diye var.
   - Basit kelime kurallarıyla kategori tahmin eder.
   - Mesela `faiz`, `dolar`, `enflasyon` geçerse ekonomi diyebilir.

Fallback analyzer gerçek çözüm değil. Sadece "pipeline baştan sona çalışıyor mu?" diye bakmak için var.

## 6. JSONB Neden Önemli?

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

## 7. JSONB'nin Kötü Tarafı Var mı?

Var.

JSONB esnek ama her şeyi JSONB'ye atmak da iyi değil. Çok sık sorgulanacak alanlar için index gerekir.

Bu yüzden örnek olarak kategori index'i ekledim:

```sql
CREATE INDEX idx_news_documents_category
    ON news_documents ((payload #>> '{analysis,category}'));
```

Yani veri esnek kalıyor ama kategoriye göre sorgu da hızlanabiliyor.

## 8. `content_hash` Neden Var?

Aynı haber tekrar gelirse Postgres'e tekrar tekrar eklenmesin diye.

Mantık basit:

```text
kaynak + haber linki -> hash
```

Bu hash unique. Aynı haber tekrar gelirse yeni kayıt açmak yerine mevcut kayıt güncellenir.

## 9. Şu Ana Kadar Ne Çalıştı?

Test:

```bash
make test
```

Sonuç:

```text
Ran 3 tests
OK
```

Dry-run:

```bash
make dry-run
```

Son denemede:

- 9 kaynak config'te vardı.
- Normal web crawling ile 14 haber payload'ı oluştu.
- Anadolu Ajansı header hatası verdi ama pipeline durmadı.
- Çıktı `outputs/latest_payloads.jsonl` dosyasına yazıldı.

## 10. Şu An Eksikler

- Docker Desktop kapalı olduğu için Postgres yazma adımını canlı denemedim.
- OpenAI API key ile gerçek LLM çıktısını henüz denemedim.
- Normal web crawling'e geçti ama her sitenin HTML yapısı farklı olduğu için selector/parser kısmı geliştirilecek.
- Anadolu Ajansı için ayrı header/parser ayarı gerekebilir.
- Kaynakların kullanım şartlarına bakmak lazım.
- Kategoriler hocayla konuşup netleşmeli.

## 11. Hocaya Nasıl Anlatırım?

Kısa anlatım:

```text
Hocam kaynakları config'e aldım. RSS yerine normal web sayfasından haber linklerini bulup haber sayfasına giren bir crawler akışı kurdum. LLM tarafında kategori, özet, keyword ve sentiment çıkaracak yapı var. Sonucu Postgres'te tek payload jsonb alanında tutuyorum. Böyle yaptım çünkü ileride çıkarılacak alanlar değişirse tabloyu sürekli değiştirmek gerekmeyecek.
```

## 12. Bir Sonraki Adım

Sıradaki iş bence şu:

1. Docker Desktop açıp Postgres yazmayı denemek.
2. OpenAI API key ile `make dry-run-llm` çalıştırmak.
3. LLM'in 2-3 haber için doğru kategori verip vermediğine bakmak.
4. Hocayla kategori listesini netleştirmek.
5. JSONB üzerinden örnek SQL sorguları eklemek.
