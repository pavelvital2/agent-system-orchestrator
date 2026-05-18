.PHONY: install test smoke doctor lint

PYTHON ?= python3
ASO_SCRIPT := agent-system/tools/aso/aso.py

install:
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m unittest discover -s agent-system/tools/aso/tests

smoke:
	$(PYTHON) $(ASO_SCRIPT) --help >/dev/null
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) status --root . --mode package
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) lint --root . --mode package --strict

doctor:
	@echo "aso doctor is reserved for Stage 1 task 002 and is not implemented by TASK_ASO_STAGE1_DEV_001_PACKAGING."
	@echo "Run 'make smoke' or 'make lint' for the safe Stage 1 packaging checks available now."

lint:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) lint --root . --mode package --strict
