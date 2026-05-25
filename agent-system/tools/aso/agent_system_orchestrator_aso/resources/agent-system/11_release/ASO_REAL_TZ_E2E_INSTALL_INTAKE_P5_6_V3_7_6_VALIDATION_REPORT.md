# ASO Real-TZ E2E Install and Intake P5.6 v3.7.6 Validation Report

## Task

- Task ID: `TASK_ASO_E2E_FIX_080_RELEASE_VALIDATION_AND_DOCS`
- Role: tech_writer
- Branch: `correction/aso-real-tz-e2e-fixes-p5.6-v3.7.6`
- Validation date: 2026-05-24

## Version Tuple

- Package version: 3.7.6
- Governance ruleset: 3.7.6
- Runtime schema: 3.1.1
- Artifact package schema: 1.1.0

## Scope

- Release notes finalized at
  `agent-system/11_release/ASO_REAL_TZ_E2E_INSTALL_INTAKE_P5_6_V3_7_6_RELEASE_NOTES.md`.
- Governance changelog entry `GOV-2026-05-24-001` is present with
  `STATUS: accepted`.
- README and install documentation describe the official installed ASO
  real-TZ workflow and unsupported installation/bootstrap patterns.
- Scope reconciliation: task packet requirement 1 explicitly requires updating
  package/governance version metadata to `3.7.6 / 3.7.6`; therefore the
  retained metadata files are `pyproject.toml`,
  `agent-system/tools/aso/agent_system_orchestrator_aso/__init__.py`, and
  `agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/runtime_schema_contracts.py`.
- Scope reconciliation: validator/current-tuple docs and their packaged
  resource copy are retained so installed ASO reports the same active
  `3.7.6 / 3.7.6 / 3.1.1 / 1.1.0` tuple as the source checkout.
- Scope reconciliation: focused metadata tests are retained because they prove
  package version coherence and the P5.6 authority-map tuple.
- Final validation evidence below follows
  `project-input/aso_real_tz_e2e_fixes_p5_6_v3_7_6/07_VALIDATION/VALIDATION_COMMANDS.md`.

## Expected Acceptance Evidence

- `[test]` extra installs `jsonschema>=4.22`.
- Clean installer leaves the live checkout status unchanged.
- Installed CLI runs against an external workspace with a real TZ document.
- `state init`, `intake bootstrap`, and `state verify --strict` pass.
- `plan-next --strict` is read-only and recommends dispatch-capable
  `CREATE_AGENT`.
- Forbidden runtime/input/archive roots are not tracked.

## Local Validation Results

Validation commands were run with the P5.6 release metadata and documentation
edits present in the working tree.

| Command | Result |
| --- | --- |
| `git status --short --branch` | passed; only P5.6 release/metadata edits and new release docs were present after generated build metadata cleanup |
| `git diff --check` | passed |
| `PYTHONDONTWRITEBYTECODE=1 make test` | passed; source hygiene passed, 376 ASO tests OK, and 6 top-level tests OK |
| `PYTHONDONTWRITEBYTECODE=1 make smoke` | passed; package status, lint, doctor, package-layout, validators, state verify/render, plan-next, dashboard, checkpoint-preflight, and 18 governance smoke assertions passed with active `3.7.6 / 3.7.6 / 3.1.1 / 1.1.0` |
| `PYTHONDONTWRITEBYTECODE=1 make ci` | passed; source hygiene, full test discovery, smoke, doctor, lint, clean install smoke, and final `git diff --check` passed |
| test extra install check | passed; fresh `/tmp/aso_p56_test_extra_venv` installed editable `agent-system-orchestrator-3.7.6` with `jsonschema 4.26.0` |
| official safe install check | passed; `install_aso_clean.sh --source "$ASO_ROOT" --venv /tmp/aso_p56_clean_install_venv --source-copy /tmp/aso_p56_clean_install_src --with-test`, `aso --help`, `aso status --root "$ASO_ROOT" --mode package`, `jsonschema 4.26.0`, and before/after git status diff passed |
| installed CLI external workspace check | passed; pre-checkpoint validation used a staged-tree archive created from the current P5.6 working tree, initialized an external workspace with the real TZ fixture, bootstrapped requirements analyst task, strict state verify passed, and `plan-next` returned dispatch-capable `CREATE_AGENT` |
| read-only plan-next mutation check | passed; SHA-256 file manifest before and after installed `aso plan-next --strict` was identical |
| `PYTHONDONTWRITEBYTECODE=1 make install-smoke` | passed; clean installed package from isolated source archive and imported ASO from virtualenv `site-packages` |
| `PYTHONDONTWRITEBYTECODE=1 make e2e-real-tz-smoke` | passed; 2 real-TZ E2E smoke tests OK |
| `git ls-files project-input project-runtime project-archive .venv` | passed; empty output |

## Command Notes

The validation packet's installed workspace example uses
`cp 09_FIXTURES/TZ_REAL_E2E_TELEGRAM_BOT.md ...` from its packet directory.
The equivalent repo-root command used the committed fixture path
`agent-system/tests/fixtures/real_tz_e2e/TZ_REAL_E2E_TELEGRAM_BOT.md`.

Pre-checkpoint installed-package validation must not use `git archive HEAD`,
because `HEAD` still points at the previous package metadata until the P5.6
checkpoint is committed. The installed external workspace check used a
staged-tree archive (`git add ...`, `git write-tree`, `git archive <tree>`) so
the installed package metadata, console script, packaged validator resources,
and real-TZ workflow evidence all came from the current `3.7.6` working tree.
After checkpoint, `git archive HEAD` is expected to provide equivalent evidence
for the committed P5.6 tree.

## Result

- STATUS: passed-final-validation
- BLOCKERS: none
- FINAL_REMOTE_CI_FOR_CURRENT_HEAD: not claimed by this local release task.
