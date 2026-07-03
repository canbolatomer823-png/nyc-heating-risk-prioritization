# Server Deploy Runbook

Bu proje tek dosyalık `outputs/dashboard.html` üretiyor. Server deploy tarafı bilerek küçük ve izole tutuldu.
Mentorun verdiği serverda Apache zaten çalıştığı için ana deploy yöntemi:

1. Dashboard'u küçük bir `uvicorn` servisiyle `127.0.0.1` üstünde çalıştır.
2. Apache'ye sadece yeni bir reverse proxy path'i ekle.
3. Mevcut Apache vhostlarını, Docker containerlarını ve servisleri bozma.

## 1. Server'a Girince Önce Kontrol Et

Root yetkisiyle girildiği için ilk adım sadece okuma/kontrol olmalı:

```bash
cd projects/news-llm-postgres
make server-preflight
```

Bu script şunlara bakar:

- İşletim sistemi
- Disk ve memory
- Dinleyen portlar
- Docker ve Docker Compose durumu
- Çalışan containerlar
- Nginx/Apache/Caddy var mı
- Firewall durumu
- Seçilen port dolu mu

Script bilinçli olarak `apt install`, `reboot`, `docker prune`, `systemctl stop` veya firewall değişikliği yapmaz.

## 2. Projeyi Hazırla

```bash
git clone https://github.com/canbolatomer823-png/nyc-heating-risk-prioritization.git
cd nyc-heating-risk-prioritization
git checkout codex/news-llm-postgres-draft

cd projects/news-llm-postgres
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Dashboard üret:

```bash
make PYTHON=.venv/bin/python dry-run dashboard
```

OpenAI key varsa:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
make PYTHON=.venv/bin/python dry-run-llm dashboard
```

## 3. Apache Arkasında Uvicorn ile Yayına Al

Paketli ve düşük disk kullanan yöntem:

```bash
mkdir -p /opt/omer-news-dashboard
cp outputs/dashboard.html /opt/omer-news-dashboard/dashboard.html
cp deploy/server/asgi_dashboard.py /opt/omer-news-dashboard/asgi_dashboard.py
```

Uvicorn'u önce elle dene:

```bash
cd /opt/omer-news-dashboard
uvicorn asgi_dashboard:app --host 127.0.0.1 --port 8011
```

Ayrı terminalden kontrol:

```bash
curl http://127.0.0.1:8011/health
curl -I http://127.0.0.1:8011/
curl http://127.0.0.1:8011/metadata
```

Kalıcı servis örneği:

```bash
deploy/server/systemd/omer-news-dashboard.service.example
```

Apache proxy örneği:

```bash
deploy/server/apache-uvicorn-proxy.example.conf
```

Örnek dış URL:

```text
https://DOMAIN/omer-news-dashboard-live/
```

Bu yöntemde Apache sadece `/omer-news-dashboard-live/` path'ini `127.0.0.1:8011` adresine taşır.
Mevcut siteler ve vhostlar değişmeden kalır.

## 4. Docker Alternatifi

Varsayılan port `18080`. Bu port sadece localhost'a bind edilir:

```bash
make dashboard-up
```

Farklı port gerekiyorsa:

```bash
NEWS_DASHBOARD_PORT=18081 make dashboard-up
```

Kontrol:

```bash
curl http://127.0.0.1:18080/health
curl -I http://127.0.0.1:18080/
make server-verify
```

Log:

```bash
make dashboard-logs
```

Durdurma:

```bash
make dashboard-down
```

`make server-verify` sonucu `outputs/deploy-proof.json` dosyasına yazılır. Bu dosya deploy sonrası kanıt olarak saklanabilir.

## 5. Dashboard'u Güncel Tut

Manuel refresh:

```bash
make server-refresh
```

Varsayılan olarak fallback analyzer çalışır. LLM ile güncellemek için:

```bash
export OPENAI_API_KEY="..."
NEWS_ANALYZER=auto make server-refresh
```

Cron örneği:

```bash
deploy/server/crontab.example
```

Systemd timer örneği:

```bash
deploy/server/systemd/news-dashboard-refresh.service.example
deploy/server/systemd/news-dashboard-refresh.timer.example
```

Not: Bu örnekler otomatik kurulmaz. Mevcut crontab veya systemd dosyaları önce kontrol edilmeli, sonra yeni kayıt eklenmeli.

## 6. DNS Gelirse

DNS kaydı örnek:

```text
dashboard.example.com A 78.135.87.56
```

Sonra server'daki mevcut reverse proxy düzenine göre sadece yeni site eklenir. Mevcut dosyalar ezilmez.

Nginx örneği:

```bash
deploy/server/nginx-reverse-proxy.example.conf
```

Caddy örneği:

```bash
deploy/server/Caddyfile.example
```

Apache + uvicorn path proxy örneği:

```bash
deploy/server/apache-uvicorn-proxy.example.conf
```

DNS bağlandıktan sonra dışarıdan kontrol:

```bash
curl -I http://dashboard.example.com/
curl http://dashboard.example.com/health
```

HTTPS gerekiyorsa Caddy otomatik sertifika alabilir. Nginx kullanılacaksa serverdaki mevcut certbot/SSL düzeni bozulmadan yeni domain için sertifika eklenmeli.

## 7. Paketli Taşıma

Repo klonlamak yerine sadece dashboard ve server dosyalarını taşımak için:

```bash
make server-package
```

Bu komut `outputs/server-bundle/` altında `.tar.gz` üretir.

## 8. Dikkat Edilecekler

Bu komutları düşünmeden çalıştırma:

```bash
docker system prune
docker compose down
systemctl stop apache2
systemctl restart apache2
ufw reset
apt upgrade -y
reboot
kill -9 ...
```

Eğer gerekirse önce mevcut servislerin kime ait olduğu ve hangi portu kullandığı netleştirilmeli.

## Hocaya Kısa Teknik Açıklama

Bu deploy yaklaşımında dashboard doğrudan dış dünyaya açılmıyor. Önce `uvicorn` ile `127.0.0.1:8011` üstünde çalışıyor, Apache de sadece yeni bir path'i bu servise proxy ediyor. Böylece mevcut Apache siteleri, Docker containerları ve servis portları ezilmemiş oluyor.
