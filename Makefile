PY := .venv/bin/python
PIP := .venv/bin/pip
API := http://127.0.0.1:8083
MONTH ?= $(shell date +%Y-%m)

.PHONY: setup test render-sample evaluate-sample run-api clean \
        remarkable-status sync-remarkable-dry sync-remarkable nightly-run render-month

setup:
	python3 -m venv .venv
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"
	$(PY) -m playwright install chromium

render-sample:
	$(PY) -m packages.renderer.render_month data/sample_month.json

evaluate-sample:
	$(PY) -m packages.core.evaluate data/sample_events.json

run-api:
	$(PY) -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8083

test:
	$(PY) -m pytest -q

clean:
	rm -rf .venv .pytest_cache *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

service-restart:
	./scripts/restart_service.sh

service-update:
	./scripts/update_service.sh

service-logs:
	tail -f ~/Library/Logs/HabitOS/api.out.log ~/Library/Logs/HabitOS/api.err.log

service-status:
	launchctl print gui/$$(id -u)/com.pratyush.habitos.api

remarkable-status:
	curl -s "$(API)/remarkable/status" | $(PY) -m json.tool

sync-remarkable-dry:
	@echo "Dry-run sync for $(MONTH) — no files will be uploaded"
	curl -s -X POST "$(API)/remarkable/sync?month=$(MONTH)&dry_run=true" | $(PY) -m json.tool

sync-remarkable:
	@echo "Syncing $(MONTH) to reMarkable…"
	curl -s -X POST "$(API)/remarkable/sync?month=$(MONTH)&dry_run=false" | $(PY) -m json.tool

nightly-run:
	curl -s -X POST "$(API)/automation/nightly-run?dry_run=false" | $(PY) -m json.tool

render-month:
	curl -s -X POST "$(API)/render/month?month=$(MONTH)" | $(PY) -m json.tool

run-admin:
	pnpm --dir apps/admin dev

admin-types:
	pnpm --dir apps/admin api-types