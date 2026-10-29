.PHONY: setup kb test lint api smoke

setup:            ## create venv and install the API with dev tools
	cd api && uv venv && uv pip install -e ".[dev]"

kb:               ## build data/generated/kb.json from the local crawl
	python scripts/extract_kb.py

test:
	cd api && pytest -q

lint:
	cd api && ruff check . && ruff format --check .

api:              ## run the API with reload on :8000
	cd api && uvicorn parklens.main:app --reload --port 8000

smoke:            ## one real call to the Meta Model API
	python scripts/smoke_test.py
