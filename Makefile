# Mağaza Asistanım — developer entry points. Recipes run in bash (Git Bash on Windows).
SHELL := /bin/bash
export PYTHONUTF8 := 1
export PYTHONIOENCODING := utf-8
.DEFAULT_GOAL := help
.PHONY: help setup dev check lint typecheck test test-py test-js e2e eval contracts data fixture seed build clean

UV ?= uv
PNPM ?= pnpm
WITH_EMU := bash scripts/with-emulator.sh

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install dependencies (uv, pnpm), Playwright browsers, Firestore emulator, demo data
	$(UV) sync --all-packages
	$(PNPM) install
	$(PNPM) exec playwright install chromium
	$(UV) run playwright install chromium
	@ls $$HOME/.cache/firebase/emulators/cloud-firestore-emulator-*.jar >/dev/null 2>&1 || $(PNPM) exec firebase setup:emulators:firestore
	$(MAKE) data

check: lint typecheck test ## Lint, type-check and unit tests (Python + TS)

lint: ## ruff + eslint
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(PNPM) exec eslint . --max-warnings=0

typecheck: ## mypy + tsc
	$(UV) run mypy
	$(PNPM) -r run typecheck
	$(PNPM) exec tsc -p tsconfig.e2e.json

test: test-py test-js ## Unit tests (pytest against the Firestore emulator, vitest)

test-py:
	$(WITH_EMU) uv run pytest -q

test-js:
	$(PNPM) -r run test

contracts: ## Generate TS types and Pydantic models from JSON Schema
	$(PNPM) --filter @magaza/contracts run generate

data: ## Generate deterministic demo catalogs, feeds, data sheets and images
	$(UV) run python -m magaza_jobs.demo_data --out data/demo

fixture: ## Generate the 90-day synthetic analytics fixture (DuckDB)
	$(UV) run python -m magaza_jobs.simulator --out data/analytics/fixture.duckdb

seed: ## Load demo tenants + catalogs into the running Firestore emulator
	$(UV) run python -m magaza_jobs.seed --data data/demo

build: ## Build widget, both demo storefronts and admin-web
	$(PNPM) --filter @magaza/widget run build
	$(PNPM) --filter @magaza/demo-store run build:all
	$(PNPM) --filter @magaza/admin-web run build

dev: ## Firestore emulator + all services + apps
	node scripts/dev.mjs

e2e: build ## Playwright end-to-end tests; screenshots go to artifacts/screenshots/
	@test -d data/demo || $(MAKE) data
	@test -f data/analytics/fixture.duckdb || $(MAKE) fixture
	$(WITH_EMU) "uv run --no-sync python -m magaza_jobs.seed --data data/demo && pnpm exec playwright test"

eval: ## Run adk eval golden sets (FakeLlm unless LLM_MODE=vertex)
	$(WITH_EMU) "uv run --no-sync python -m magaza_jobs.seed --data data/demo && uv run --no-sync python services/agent-api/evals/run_evals.py"

clean: ## Remove build outputs
	rm -rf apps/*/dist apps/demo-store/out apps/demo-store/.next playwright-report test-results
