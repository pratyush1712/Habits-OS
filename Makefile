PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: setup test render-sample evaluate-sample run-api clean

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
	.venv/bin/uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

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