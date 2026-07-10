.PHONY: install lint test eval

install:
	cd backend && pip install -e ".[dev]"

lint:
	cd backend && ruff check . && black --check . && mypy app

test:
	cd backend && pytest -q

eval:
	python3 evals/run_evals.py --mode offline
