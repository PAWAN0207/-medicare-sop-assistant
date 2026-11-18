PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
.PHONY: setup ingest run test eval eval-live openapi report

setup:            ## 1. create venv + install deps
	$(PY) -m venv .venv && .venv/bin/pip install -q -r requirements.txt
	@test -f .env || cp .env.example .env

ingest:           ## index a snapshot folder (default: original library). Idempotent.
	$(PY) -m sopassist.ingest.cli $(or $(SNAPSHOT),data/sops)

run: ingest       ## index original library, then serve the API on :8000 (docs at /docs)
	$(PY) -m uvicorn sopassist.main:app --host 0.0.0.0 --port 8000

test:             ## offline, deterministic, no API key
	PROVIDER=fake DB_PATH=:memory: $(PY) -m pytest tests -q

eval:             ## offline evaluation (fake LLM) -> docs/eval_results.md
	PROVIDER=fake $(PY) -m sopassist.eval.run_eval --compare-modes

eval-live:        ## evaluation with the real LLM from .env -> docs/eval_results_live.md
	PROVIDER=openai_compat $(PY) -m sopassist.eval.run_eval --compare-modes --out docs/eval_results_live.md

openapi:
	$(PY) -c "import json; from sopassist.api.app import create_app; print(json.dumps(create_app().openapi(), indent=2))" > docs/openapi.json

report:           ## regenerate docs/test_report.md
	PROVIDER=fake DB_PATH=:memory: $(PY) -m pytest tests -v -p no:cacheprovider 2>&1 | tee docs/test_report.raw
