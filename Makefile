.PHONY: install install-test install-user verify-install install-smoke test smoke doctor lint source-hygiene ci

PYTHON ?= python3
ASO_SCRIPT := agent-system/tools/aso/aso.py
VENV ?= .venv
ASO_BIN := $(VENV)/bin/aso

install:
	$(PYTHON) -m pip install -e .

install-test:
	$(PYTHON) -m pip install -e ".[test]"

install-user:
	PYTHONDONTWRITEBYTECODE=1 bash install.sh --python "$(PYTHON)" --venv "$(VENV)"

verify-install:
	test -x "$(ASO_BIN)"
	PYTHONDONTWRITEBYTECODE=1 "$(ASO_BIN)" --help >/dev/null
	PYTHONDONTWRITEBYTECODE=1 "$(ASO_BIN)" status --root . --mode package
	PYTHONDONTWRITEBYTECODE=1 "$(ASO_BIN)" project create --help >/dev/null
	PYTHONDONTWRITEBYTECODE=1 "$(ASO_BIN)" project verify-clean --help >/dev/null
	PYTHONDONTWRITEBYTECODE=1 "$(ASO_BIN)" lint --root . --mode package --strict
	PYTHONDONTWRITEBYTECODE=1 "$(ASO_BIN)" doctor --root . --mode package --strict
	PYTHONDONTWRITEBYTECODE=1 "$(ASO_BIN)" package-layout verify --root . --strict

install-smoke:
	tmp_dir="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmp_dir"' EXIT; \
	PYTHONDONTWRITEBYTECODE=1 bash agent-system/scripts/install_aso_clean.sh --source . --venv "$$tmp_dir/venv" --python "$(PYTHON)"; \
	PYTHONDONTWRITEBYTECODE=1 "$$tmp_dir/venv/bin/aso" --help >/dev/null; \
	PYTHONDONTWRITEBYTECODE=1 "$$tmp_dir/venv/bin/aso" status --root . --mode package; \
	PYTHONDONTWRITEBYTECODE=1 "$$tmp_dir/venv/bin/aso" package-layout verify --root . --mode package --strict; \
	PYTHONDONTWRITEBYTECODE=1 "$$tmp_dir/venv/bin/python" -c "import importlib.metadata as md, json, pathlib; import agent_system_orchestrator_aso, agent_system_orchestrator_aso.cli as cli; dist = md.distribution('agent-system-orchestrator'); direct_url = json.loads(dist.read_text('direct_url.json') or '{}'); source = pathlib.Path(agent_system_orchestrator_aso.__file__).resolve().as_posix(); assert direct_url.get('dir_info', {}).get('editable') is not True, direct_url; assert '/site-packages/agent_system_orchestrator_aso/__init__.py' in source, source; assert callable(cli.main), cli.main; print(source)"

test: source-hygiene
	$(PYTHON) -m unittest discover -s agent-system/tools/aso/tests
	$(PYTHON) -m unittest discover -s agent-system/tests

smoke:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) --help >/dev/null
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) status --root . --mode package
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) project create --help >/dev/null
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) project verify-clean --help >/dev/null
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) lint --root . --mode package --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) doctor --root . --mode package --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) package-layout verify --root . --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) validate-design agent-system/tests/fixtures/design/valid_design.md --root . --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) validate-context-pack agent-system/tests/fixtures/context_pack/valid_context_pack.json --root . --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) validate-rules --root . --strict
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) state verify --root agent-system/tests/fixtures/state/valid_workspace --strict --json-out /tmp/aso-stage2-state-smoke.json
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) state verify --root agent-system/tests/fixtures/state/p2_valid_workspace --strict --json-out /tmp/aso-p2-state-smoke.json
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) state render --root agent-system/tests/fixtures/state/p2_valid_workspace --format json --out /tmp/aso-p2-state-render-smoke.json
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) plan-next --root agent-system/tests/fixtures/state/valid_workspace --strict --json-out /tmp/aso-stage2-plan-smoke.json
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) dashboard --root agent-system/tests/fixtures/state/valid_workspace --out /tmp/aso-stage2-dashboard-smoke.html
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) checkpoint-preflight --root . --mode package --strict --json-out /tmp/aso-stage2-checkpoint-preflight-smoke.json
	PYTHONDONTWRITEBYTECODE=1 ./agent-system/scripts/run_governance_smoke_tests.sh

doctor:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) doctor --root . --mode package --strict

lint:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(ASO_SCRIPT) lint --root . --mode package --strict

source-hygiene:
	PYTHONDONTWRITEBYTECODE=1 bash agent-system/scripts/source_hygiene.sh

ci: test smoke doctor lint install-smoke
	git diff --check
