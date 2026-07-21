SPECVERSIONS := v1.0.0 v1.2.0 v1.3.0

.PHONY: generate test lint format

generate:
	@for v in $(SPECVERSIONS); do \
		echo "Generating types for $$v..."; \
		python3 generate.py $$v || exit 1; \
	done

test:
	python3 -m pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .
