# Server Deploy Notu

Bu dashboard tek dosyalık HTML ürettiği için ilk server deploy'u basit tutuldu:

1. Python pipeline `outputs/dashboard.html` üretir.
2. Nginx container bu dosyayı yayınlar.
3. Daha sonra cron ile belli aralıklarla `make dry-run-llm dashboard` çalıştırılabilir.

## Server Gereksinimleri

- Ubuntu server
- Docker ve Docker Compose plugin
- Git
- Python 3.10+ veya sistemde kurulu uygun Python

## İlk Kurulum

```bash
git clone https://github.com/canbolatomer823-png/nyc-heating-risk-prioritization.git
cd nyc-heating-risk-prioritization
git checkout codex/news-llm-postgres-draft

cd projects/news-llm-postgres
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Dashboard Üret

API key yoksa fallback analyzer ile:

```bash
make PYTHON=.venv/bin/python dry-run dashboard
```

OpenAI ile:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
make PYTHON=.venv/bin/python dry-run-llm dashboard
```

## Nginx ile Yayınla

```bash
NEWS_DASHBOARD_PORT=8080 docker compose -f deploy/server/compose.yaml up -d
```

Kontrol:

```bash
curl http://localhost:8080/health
curl -I http://localhost:8080/
```

## Domain veya Reverse Proxy

Serverda ayrıca Nginx varsa domaini container'a yönlendirmek için örnek:

```nginx
server {
    listen 80;
    server_name dashboard.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Güncelleme Akışı

```bash
git pull
source .venv/bin/activate
make PYTHON=.venv/bin/python dry-run-llm dashboard
docker compose -f deploy/server/compose.yaml restart news-dashboard
```

Not: Dashboard HTML dosyası volume olarak bağlandığı için çoğu durumda container restart gerekmez; sayfayı yenilemek yeterlidir. Restart komutu sadece garanti kontrol için yazıldı.
