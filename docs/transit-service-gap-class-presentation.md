# 30 Dakikalık Sınıf Anlatım Planı

Bu akış, projeyi tahtada veya kısa slaytlarla anlatırken dağılmaman için hazırlandı. Hedef, 30 dakikada hem teknik derinlik göstermek hem de "Bu neye çare oluyor?" sorusuna net cevap vermektir.

## 1. Sunumun tek cümlelik özeti

`Gerçek zamanlı otobüs verisi, hava durumu ve mahalle kırılganlık verisini birleştirerek hangi hat ve duraklarda ciddi servis boşluğu riski oluşacağını tahmin eden ve bu riskin kimleri daha fazla etkilediğini gösteren bir sistem geliştirdim.`

Bu cümleyi en başta ve en sonda kullan.

## 2. 30 dakikalık zaman planı

### Dakika 0-3
- problemi anlat
- neden önemli olduğunu söyle
- neden klasik gecikme tahmini yapmadığını açıkla

### Dakika 3-7
- veri kaynaklarını anlat
- verilerin neden gerçek ve güvenilir olduğunu açıkla

### Dakika 7-12
- problem formülasyonunu anlat
- hedef değişkenleri ve hipotezleri yaz

### Dakika 12-18
- mimariyi anlat
- Python, SQL, R, AWS, Docker, Kubernetes rollerini ayır

### Dakika 18-23
- istatistiksel modeli anlat
- mixed-effects regression ve ANOVA neden seçildiğini savun

### Dakika 23-27
- elde ettiğin çıktıları ve beklenen aksiyonu göster
- operasyonel ve toplumsal etkiyi bağla

### Dakika 27-30
- sınırlılıkları dürüstçe söyle
- gelecekteki geliştirmeyi ekle
- sorulara geç

## 3. Tahtaya yazılacak akış

Tahtayı 6 parçaya böl.

### Bölüm 1: Problem

Tahtaya yaz:

`Problem: Transit delay != gerçek sorun`

Altına:
- düzensiz araç aralıkları
- uzun servis boşluğu
- eşitsiz etki

Söylenecek cümle:
- "Ben sadece araç gecikti mi sorusunu değil, bu bozulma yolcuyu nerede daha ağır vuruyor sorusunu ele aldım."

### Bölüm 2: Veri kaynakları

Tahtaya yaz:

`MTA + GTFS + NOAA + Census CRE`

Altına kısa not:
- MTA: gerçek zamanlı otobüs verisi
- GTFS: planlanan servis yapısı
- NOAA: hava etkisi
- CRE: mahalle kırılganlığı

Söylenecek cümle:
- "Tamamı resmi kaynaklardan geldiği için veri uydurma ya da sentetik senaryo yok."

### Bölüm 3: Hedef

Tahtaya yaz:

`Y1 = high_service_gap_risk`

`Y2 = equity_weighted_gap_score`

Söylenecek cümle:
- "Birinci çıktı operasyon ekipleri için, ikinci çıktı ise bu bozulmanın toplumsal etkisini ölçmek için kullanılıyor."

### Bölüm 4: Özellikler

Tahtaya yaz:

- saat
- gün
- planlanan headway
- gerçek headway
- rolling delay
- yağış
- sıcaklık
- tract vulnerability

Söylenecek cümle:
- "Özellikleri sadece tahmin gücü için değil, açıklanabilirlik için de seçtim."

### Bölüm 5: Model

Tahtaya yaz:

`logit(P(risk=1)) = Xb + u_route + u_stop`

Söylenecek cümle:
- "Aynı hat ve durak içinde tekrar eden örüntüler olduğu için klasik lojistik regresyon yerine mixed-effects yapı kullandım."

Ardından yaz:

`ANOVA / LRT -> model katkısı`

Söylenecek cümle:
- "Bazı değişkenlerin gerçekten anlamlı katkı verip vermediğini ANOVA ve likelihood ratio test ile kontrol ettim."

### Bölüm 6: Mimari

Tahtaya yaz:

`API -> S3 raw -> SQL features -> train -> model -> FastAPI -> EKS`

Söylenecek cümle:
- "AWS ve Kubernetes burada süs değil; veri alma, eğitim ve servis etme katmanlarını ayrıştırmak için kullanıldı."

## 4. Slayt veya tahta başlıkları

Eğer slayt kullanacaksan başlıkları aynen böyle kur:

1. Problem neden önemli
2. Neden bu proje klişe değil
3. Gerçek veri kaynakları
4. Veri modeli ve hedef değişken
5. Feature engineering
6. İstatistiksel yöntem
7. AWS mimarisi
8. Sonuçlar ve önerilen aksiyon
9. Sınırlılıklar
10. Gelecek çalışma

## 5. Hocaların sorabileceği kritik sorular ve cevap iskeletleri

### Soru 1
`Bu proje tam olarak neye çare oluyor?`

Cevap:
- Transit işletmecisinin kaynak kısıtında hangi hat-durak-zaman dilimlerine müdahale etmesi gerektiğini gösteriyor.
- Sadece gecikmeyi değil, hizmet bozulmasının toplumsal yükünü de ölçüyor.

### Soru 2
`Neden makine öğrenmesi yerine regresyon kullandın?`

Cevap:
- Ana hedefim sadece tahmin değil, etkiyi yorumlamak.
- Regresyon sayesinde yağışın, headway'in ve mahalle kırılganlığının risk üzerindeki katkısını açıklayabiliyorum.
- Buna rağmen performans kıyası için XGBoost benchmark'ı kullandım.

### Soru 3
`Neden Kubernetes kullandın?`

Cevap:
- Ingest, eğitim ve API işlerini ayrı konteynerlerde çalıştırmak istedim.
- Eğitim işi batch, API işi sürekli çalışan servis olduğu için K8s doğal ayrım sağladı.
- 15 günlük kapsamda sadece gerekli parçayı kullandım.

### Soru 4
`Bu proje gerçek hayatta nerede uygulanır?`

Cevap:
- belediye otobüs işletmeleri,
- şehir içi ulaşım planlama ekipleri,
- toplu taşıma performans izleme birimleri,
- sosyal politika ve ulaşım eşitliği çalışan kurumlar.

### Soru 5
`Bu proje neden özgün?`

Cevap:
- Çünkü gecikme tahmini yapan çok çalışma var ama servis bozulmasını sosyal kırılganlıkla birleştirip operasyonel karar desteğine dönüştüren daha niş ve daha uygulanabilir bir çerçeve sunuyorum.

### Soru 6
`Limitasyonun ne?`

Cevap:
- API erişim sınırlamaları,
- eksik veya düzensiz realtime kayıtlar,
- area-level sosyal veriden bireysel nedensellik çıkaramama,
- 15 günlük kapsam nedeniyle üretim seviyesi tam otomasyon yerine güçlü MVP hedefleme.

## 6. Sunumda özellikle söylemen gereken teknik doğrular

- "Bu çalışma sentetik veriyle yapılmadı."
- "Veri kaynakları resmi ve programatik erişime açık."
- "Model seçimi yorumlanabilirlik hedefiyle yapıldı."
- "SQL sadece veri çekmek için değil, feature üretmek için kullanıldı."
- "R tarafını istatistiksel anlamlılık ve raporlama için kullandım."
- "AWS tarafında gerçek dağıtım senaryosuna yakın kaldım ama gereksiz servis şişkinliğine gitmedim."

## 7. 3 dakikalık kısa özet versiyonu

Eğer hoca "çok uzatma, projeyi özetle" derse şu akışı kullan:

1. Gerçek zamanlı otobüs verisi, hava verisi ve mahalle kırılganlık verisini birleştirdim.
2. Amaç sadece gecikme tahmini yapmak değildi; hangi bölgelerde ciddi servis boşluğu oluşacağını ve bunun kimleri daha ağır etkileyeceğini ölçmekti.
3. Bunun için mixed-effects logistic regression ile açıklanabilir bir risk modeli kurdum, ardından XGBoost ile benchmark yaptım.
4. Veriyi Python ile topladım, SQL ile feature ürettim, R ile istatistiksel testleri yaptım.
5. Sistemi Docker ile paketleyip AWS S3 ve EKS üstünde çalışacak şekilde tasarladım.
6. Çıktı olarak operasyon ekibine risk sıralaması ve eşitsizlik odaklı müdahale önerisi sunuyorum.

## 8. 1 dakikalık savunma cümlesi

`Benim projem bir şehirde otobüslerin geç kalıp kalmadığını söyleyen klasik bir model değil. Gerçek zamanlı transit verisini, hava koşullarını ve mahalle kırılganlığını bir araya getirerek hangi hat ve duraklarda ciddi servis boşluğu oluşacağını öngörüyor. Daha önemlisi, bu bozulmanın hangi toplulukları orantısız etkilediğini ölçüyor. Böylece sonuç sadece bir tahmin skoru değil, aynı zamanda operasyonel ve sosyal önceliklendirme aracı oluyor.`

## 9. Tahtaya yazılacak formüller

İki formül yeterli.

### Formül 1

`headway_gap_ratio = actual_headway / scheduled_headway`

Ne diyeceksin:
- "Servis bozulmasını sadece gecikme ile değil, planlanan aralığa göre sapma ile ölçüyorum."

### Formül 2

`logit(P(risk=1)) = b0 + b1 rain + b2 peak + b3 headway_gap + b4 vulnerability + u_route + u_stop`

Ne diyeceksin:
- "Burada rota ve durak bazlı rastgele etkiler, tekrar eden yapısal farklılıkları modelliyor."

## 10. Beklenen sonuçları nasıl anlatacaksın

Rakamlar hazır olmasa bile sonucu şu biçimde çerçevele:

- hangi değişkenler en anlamlı çıktı,
- hangi bölgelerde risk kümelendi,
- equity-weighted skor ile normal risk sıralaması arasındaki fark ne oldu,
- model operasyonel müdahale açısından nasıl kullanılabilir.

Örnek anlatım:
- "Sadece ham gecikmeye bakınca A hattı öne çıkıyordu. Ancak kırılganlık ağırlığı eklendiğinde B hattının belirli segmentleri daha öncelikli hale geldi."

## 11. Sunumu bitirirken kullanılacak kapanış

`Bu projenin katkısı tek başına daha iyi bir tahmin üretmek değil; toplu taşıma güvenilirliğini operasyonel verim ve toplumsal etki açısından birlikte ölçen uygulanabilir bir karar destek çerçevesi sunmak.`

## 12. Prova kontrol listesi

- 30 dakikayı aşma
- veri kaynaklarının adını ezberle
- neden mixed-effects kullandığını net söyle
- neden bu projenin klişe olmadığını ilk 2 dakikada açıkla
- AWS bileşenlerini sadece gerçekten kullandığın kadarıyla anlat
- sınırlılıkları gizleme
- "neye çare oluyor?" sorusuna tek cümlelik cevap hazır tut
