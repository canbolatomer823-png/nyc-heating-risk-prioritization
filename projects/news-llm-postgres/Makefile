PYTHON ?= python3
PYTHONPATH := src
DATABASE_URL ?= postgresql://news:news@localhost:54329/news

.PHONY: install test dry-run dry-run-llm dashboard server-preflight server-package server-refresh server-verify dashboard-up dashboard-down dashboard-logs db-up db-down init-db run-db

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests

dry-run:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m news_pipeline.cli \
		--sources config/sources.json \
		--limit-per-source 2 \
		--analyzer fallback \
		--output outputs/latest_payloads.jsonl

dry-run-llm:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m news_pipeline.cli \
		--sources config/sources.json \
		--limit-per-source 2 \
		--analyzer auto \
		--output outputs/latest_payloads.jsonl

dashboard:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m news_pipeline.dashboard \
		--payloads outputs/latest_payloads.jsonl \
		--patterns outputs/latest_patterns.json \
		--output outputs/dashboard.html

server-preflight:
	deploy/server/preflight.sh

server-package:
	deploy/server/package_static.sh

server-refresh:
	deploy/server/refresh_dashboard.sh

server-verify:
	deploy/server/verify_deploy.sh

dashboard-up:
	deploy/server/deploy_static.sh

dashboard-down:
	docker compose -p $${NEWS_DASHBOARD_PROJECT:-omer-news-dashboard} -f deploy/server/compose.yaml down

dashboard-logs:
	docker compose -p $${NEWS_DASHBOARD_PROJECT:-omer-news-dashboard} -f deploy/server/compose.yaml logs --tail=80

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

init-db:
	DATABASE_URL=$(DATABASE_URL) PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m news_pipeline.cli --init-db

run-db:
	DATABASE_URL=$(DATABASE_URL) PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m news_pipeline.cli \
		--sources config/sources.json \
		--limit-per-source 3 \
		--analyzer auto \
		--write-db \
		--output outputs/latest_payloads.jsonl
