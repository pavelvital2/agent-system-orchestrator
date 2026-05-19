.PHONY: install test smoke doctor lint ci

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
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) package-sync verify --root . --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) validate-design agent-system/tests/fixtures/design/valid_design.md --root . --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) validate-context-pack agent-system/tests/fixtures/context_pack/valid_context_pack.json --root . --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) validate-rules --root . --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) state verify --root agent-system/tests/fixtures/state/valid_workspace --strict --json-out /tmp/aso-stage2-state-smoke.json
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) plan-next --root agent-system/tests/fixtures/state/valid_workspace --strict --json-out /tmp/aso-stage2-plan-smoke.json
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) dashboard --root agent-system/tests/fixtures/state/valid_workspace --out /tmp/aso-stage2-dashboard-smoke.html
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) checkpoint-preflight --root . --mode package --strict --json-out /tmp/aso-stage2-checkpoint-preflight-smoke.json
	./agent-system/scripts/run_governance_smoke_tests.sh

doctor:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) doctor --root . --mode package --strict

lint:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) lint --root . --mode package --strict

ci: test smoke doctor lint
	git diff --check
