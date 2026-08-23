.PHONY: dev seed eval test up

up:            ## full stack via docker
	docker compose up --build

dev:           ## run the app locally (expects Postgres per .env / DATABASE_URL)
	uvicorn app.api:app --reload --port 8000

seed:          ## ingest the corpus (idempotent)
	python scripts/seed.py

eval:          ## reproduce the eval table
	python eval/run_eval.py

test:
	pytest -q
