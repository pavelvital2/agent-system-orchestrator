.PHONY: install test smoke doctor lint

PYTHON ?= python3
ASO_SCRIPT := agent-system/tools/aso/aso.py

install:
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m unittest discover -s agent-system/tools/aso/tests
	$(PYTHON) -m unittest discover -s agent-system/tests

smoke:
	$(PYTHON) $(ASO_SCRIPT) --help >/dev/null
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) status --root . --mode package
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) lint --root . --mode package --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) doctor --root . --mode package --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) validate-design agent-system/tests/fixtures/design/valid_design.md --root . --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) validate-context-pack agent-system/tests/fixtures/context_pack/valid_context_pack.json --root . --strict
	./agent-system/scripts/run_governance_smoke_tests.sh

doctor:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) doctor --root . --mode package --strict

lint:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) lint --root . --mode package --strict
