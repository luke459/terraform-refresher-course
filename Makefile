PYTHON ?= python3.12
PY = .venv/bin/python
NODE = runner/web/node_modules/.bin/node

.PHONY: setup terraform web serve check test test-browser test-live check-terraform state-drills check-troubleshooting image image-smoke
setup:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install -r requirements.lock
	$(PY) -m pip install --no-deps --no-build-isolation -e .
	npm --prefix runner/web ci

terraform:
	$(PY) scripts/install_terraform.py

web:
	cd runner/web && ./node_modules/.bin/node node_modules/typescript/bin/tsc --noEmit
	cd runner/web && ./node_modules/.bin/node node_modules/vite/bin/vite.js build

serve:
	.venv/bin/uvicorn runner.api.main:app --host 127.0.0.1 --port 8080

check:
	$(PY) -m compileall -q runner/api runner/cli scripts
	$(PY) scripts/check_content.py
	cd runner/web && ./node_modules/.bin/node node_modules/typescript/bin/tsc --noEmit

test:
	$(PY) -m pytest -q

test-browser: web
	cd runner/web && ./node_modules/.bin/node node_modules/@playwright/test/cli.js test

test-browser-live: web
	@test -n "$(TFPREP_AWS_PROFILE)" || (echo 'Set TFPREP_AWS_PROFILE to the explicit lab profile.'; exit 1)
	cd runner/web && ./node_modules/.bin/node node_modules/@playwright/test/cli.js test --config playwright.live.config.ts

check-terraform:
	$(PY) scripts/check_terraform.py

check-starters:
	$(PY) scripts/check_starters.py

state-drills:
	$(PY) scripts/state_drills.py

check-troubleshooting:
	$(PY) scripts/check_troubleshooting.py

test-live:
	@test -n "$(TFPREP_AWS_PROFILE)" || (echo 'Set TFPREP_AWS_PROFILE to the explicit lab profile.'; exit 1)
	$(PY) scripts/live_course.py --profile "$(TFPREP_AWS_PROFILE)"

image:
	docker compose build

image-smoke:
	$(PY) scripts/image_smoke.py
