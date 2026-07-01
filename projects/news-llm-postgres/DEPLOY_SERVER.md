# Server Deploy Runbook

Bu proje tek dosyalık `outputs/dashboard.html` üretiyor. Server deploy tarafı bilerek küçük ve izole tutuldu:

- Mevcut servisleri durdurmaz.
- Varsayılan olarak sadece `127.0.0.1:18080` üstünden yayın yapar.
- Dış erişim için mevcut Nginx/Caddy arkasına reverse proxy eklenir.
- DNS gelirse domain reverse proxy'ye bağlanır.

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

## 3. İzole Şekilde Yayına Al

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

## 4. Dashboard'u Güncel Tut

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

## 5. DNS Gelirse

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

DNS bağlandıktan sonra dışarıdan kontrol:

```bash
curl -I http://dashboard.example.com/
curl http://dashboard.example.com/health
```

HTTPS gerekiyorsa Caddy otomatik sertifika alabilir. Nginx kullanılacaksa serverdaki mevcut certbot/SSL düzeni bozulmadan yeni domain için sertifika eklenmeli.

## 6. Paketli Taşıma

Repo klonlamak yerine sadece dashboard ve server dosyalarını taşımak için:

```bash
make server-package
```

Bu komut `outputs/server-bundle/` altında `.tar.gz` üretir.

## 7. Dikkat Edilecekler

Bu komutları düşünmeden çalıştırma:

```bash
docker system prune
docker compose down
systemctl stop nginx
systemctl restart nginx
ufw reset
apt upgrade -y
reboot
kill -9 ...
```

Eğer gerekirse önce mevcut servislerin kime ait olduğu ve hangi portu kullandığı netleştirilmeli.

## Hocaya Kısa Teknik Açıklama

Bu deploy yaklaşımında dashboard container'ı dış dünyaya doğrudan açılmıyor. Önce localhost'ta izole çalışıyor, sonra DNS verilirse mevcut Nginx/Caddy üzerinden domain'e bağlanıyor. Böylece server'daki diğer servislerin portları ve configleri ezilmemiş oluyor.
