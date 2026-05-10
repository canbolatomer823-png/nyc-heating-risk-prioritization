# Müşteri Keşif Brifi – Halısaha Rezervasyon ve Topluluk Uygulaması

Bu brif, Ankara’dan başlayarak Türkiye geneline açılacak Urban FC benzeri halısaha mobil uygulamamızın ilk müşteri görüşmelerini yapılandırmak için hazırlandı. Amaç, futbol severlerin ve saha işletmelerinin gerçek ihtiyaçlarını doğrulamak, MVP kapsamını netleştirmek ve kullanılabilir veri kaynaklarını belirlemektir.

## Hedef müşteri profili
- **Oyuncular:** 18-40 yaş arası amatör futbolcular, sık sık halısaha maçı yapan arkadaş grupları, iş yeri takımları.
- **Organizatörler/Kaptanlar:** Düzenli maç organize eden ve eksik oyuncu arayan topluluk liderleri.
- **Saha işletmecileri:** Ankara’daki halısaha tesis sahipleri ve yöneticileri.
- **Platform hedefi:** iOS ve Android’de yerel dil (Türkçe) deneyimi, hızlı rezervasyon ve topluluk etkileşimi.

## Ağrı noktaları
1. Telefonla rezervasyon süreci yavaş; sahaların doluluk durumu gerçek zamanlı görülmüyor.
2. Eksik oyuncu olduğunda güvenilir ve hızlı şekilde yedek bulmak zor; “eksik sayısı” görünürlüğü yok.
3. Mevcut maçlara katılmak isteyen bireyler için uygun maçları bulma ve katılma isteği gönderme mekanizması bulunmuyor.
4. Haftanın maçları/golleri gibi topluluk içerikleri dağınık; oyuncular uygulamaya geri dönmek için motivasyon bulamıyor.
5. Ödemelerin paylaşılması, iptal politikaları ve kullanıcı güvenliği konusunda standart süreç yok.

## Değer önerimiz
- Gerçek zamanlı saha arama, slot rezervasyonu ve ödeme paylaşımı.
- Eksik oyuncu bildirimi (kaç kişi eksik, pozisyon tercihi vb.) ve katılma isteği akışı.
- Haftanın oyunu/golü, oyuncu istatistikleri ve puan/tablo içerikleriyle topluluk bağlılığı.
- Saha işletmeleri için doluluk analitikleri, kampanya yönetimi ve güvenli ödeme altyapısı.
- Saha profil kartlarında IBAN, iletişim, adres ve saha özelliklerinin şeffaf şekilde görüntülenmesi.

## Toplanacak veri envanteri
| Kaynak | Sahip | Format/Sıklık | Kritik alanlar |
| --- | --- | --- | --- |
| Saha rezervasyon sistemi | Tesis sahipleri | API, CSV, günlük | Saha ID, saat dilimleri, fiyat, doluluk |
| Kullanıcı profilleri | Ürün ekibi | Uygulama DB, gerçek zamanlı | Kişi sayısı, beceri seviyesi, konum, takım üyelikleri |
| Maç kayıtları | Organizatörler | Uygulama kayıtları | Maç tarihi, eksik oyuncu sayısı, katılım talepleri |
| Topluluk içerikleri | Pazarlama | CMS, haftalık | Haftanın maçı/golü, istatistikler, ödüller |
| Ödeme/komisyon verileri | Finans | PSP dashboard, günlük | Tutar, komisyon, iptal sayısı |
| Saha profil verileri | Saha işletmecileri | Portal, anlık | IBAN, yetkili kişi, tam adres, konum koordinatları, saha tipi |

## Başarı metrikleri ve baz çizgi
- Haftalık aktif kullanıcı (WAU) ve maç başına katılımcı sayısı.
- Rezervasyon başına onay süresi (dakika) ve iptal oranı.
- Eksik oyuncu ilanlarının dolma süresi ve katılma isteği kabul oranı.
- Saha başına doluluk oranı ve uygulama üzerinden gelen gelir payı.
- Topluluk içerikleri etkileşimi (görüntülenme, paylaşım, beğeni).

## Kritik kullanıcı yolculukları (MVP)
1. **Maç oluşturma ve saha rezervasyonu**
   - Oyuncu/kaptan uygun tarih, saat, konum ve saha tipi filtresiyle listeyi tarar.
   - Saha kartı içinde IBAN, adres, slot fiyatı ve saha kuralları görüntülenir.
   - Kullanıcı katılımcı sayısı, kişi başı ücret paylaşımı ve ödemeyi nasıl toplayacağını belirtir.
   - Rezervasyon isteği saha işletmecisine push/e-posta ile gider; onay geldiğinde tüm katılımcılara bildirim düşer.
   - Onaya kadar slot “opsiyonlu” görünür; süre dolarsa otomatik iptal edilir.

2. **Eksik oyuncu ilanı ve katılma isteği**
   - Kaptan maç kartında “Eksik sayısı” ve ihtiyaç duyulan pozisyon/beceri seviyesini girer.
   - Bölgedeki oyunculara bildirim gider; ilgilenenler maç detaylarını (saha konumu, ücret, oyun seviyesi) görür.
   - Oyuncu katılma isteği gönderir; kaptan kabul/red verir, onaylanırsa oyuncunun takvimine eklenir.
   - Ödeme paylaşımı ve IBAN bilgisi kabul ekranında tekrar gösterilir.

3. **Saha işletmesi onboarding’i**
   - İşletme sahibi portal üzerinden isim, adres, Google Maps koordinatı, saha türü (kapalı/açık), duş/otopark gibi özellikleri girer.
   - IBAN, vergi numarası ve yetkili kişi bilgisi girilir; bankayla doğrulama için otomatik mikro transfer veya belge yükleme yapılır.
   - Slot takvimi (gün, saat, fiyat) toplu CSV veya UI üzerinden yüklenir, anlık olarak uygulama listesine düşer.
   - İşletme, gelen rezervasyonları onaylayıp ödemeleri PSP üzerinden alır; panelde doluluk ve gelir raporlarını görür.

## Teknik ve veri mimarisi taslağı
- **Mobil istemciler (iOS/Android):** React Native/Flutter gibi çapraz platform çözüm; rezervasyon, eksik oyuncu, bildirimler için GraphQL/REST API çağrıları; Firebase/APNS/FCM push entegrasyonu.
- **Backend servisleri:** Node.js (NestJS) veya Python (FastAPI) tabanlı API katmanı; rezervasyon, kullanıcı, saha ve ödeme servisleri ayrı domain’lere ayrılır. Redis tabanlı slot kilitleme ile çakışmaları önler.
- **Veritabanı:** PostgreSQL (ilişkisel) + Redis (cache) + S3/Blob (belge/medya). Coğrafi sorgular için PostGIS eklentisi.
- **Ödeme & IBAN doğrulama:** Ödeme servis sağlayıcısı (iyzico, PayTR) üzerinden kart tahsilatı; IBAN doğrulaması için MASAK uyumlu KYC API’si veya bankadan mikro havale. Komisyon hesapları için PSP webhook’ları dinlenir.
- **Gerçek zamanlı güncellemeler:** Rezervasyon ve katılma istekleri için Kafka/RabbitMQ kuyruğu; mobil istemciye websocket/SSE ile slot güncellemeleri ve katılım durumu anlık gönderilir.
- **Saha işletmesi portalı:** Next.js tabanlı web panel; slot düzenleme, IBAN güncelleme, takım mesajları ve rapor modülleri.
- **Analitik & logging:** Segment/Amplitude benzeri event layer; WAU, doluluk, ilan dolma süresi gibi metrikler için günlük ETL job’u (Airflow/Glue) → Redshift/BigQuery. Exception takibi için Sentry.
- **Harita & konum:** Google Maps Platform veya Mapbox entegrasyonu; saha kartında koordinat bazlı yönlendirme ve mesafe hesaplama.

## Görüşme soruları (öneri)
1. “Son maçınızı nasıl organize ettiniz, en çok nerede zaman kaybettiniz?”
2. “Eksik oyuncu olduğunda kimi, nasıl buluyorsunuz? Kaç saat önce haber vermeniz gerekiyor?”
3. “Mevcut maçlara katılmak istediğinizde hangi kriterlere göre seçim yapıyorsunuz?”
4. “Saha işletmesi olarak rezervasyonları ve ödemeleri hangi araçlarla yönetiyorsunuz?”
5. “Haftanın golü/oyunu gibi içerikler sizi uygulamaya geri çeker mi? Hangi ödüller motive eder?”

## Keşif çıktı şablonu
- Hedef kullanıcı segmenti + ana motivasyonları + mevcut çözümleri.
- Rezervasyon ve katılım akışı (0’dan maç oluşturma ve var olan maça katılma) adımları.
- Eksik oyuncu bildirimi için gereken bilgiler (eksik sayısı, pozisyon, beceri seviyesi, ücret paylaşımı).
- Topluluk özellikleri (haftanın oyunu/golu, istatistikler) için içerik kaynakları ve yayın sıklığı.
- Saha işletmelerinin teknik entegrasyon gereksinimleri, ödeme kuralları, IBAN doğrulama süreci ve güvenlik beklentileri.

Görüşme notlarını bu şablona işleyip iki haftada bir güncelleyerek MVP önceliklerini, rezervasyon akışını ve topluluk özelliklerini gerçek kullanıcı içgörüleriyle doğrulayacağız.
