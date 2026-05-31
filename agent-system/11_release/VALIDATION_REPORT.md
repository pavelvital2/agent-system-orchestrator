# ASO Stage 1 Defect Remediation v3.8.0 Validation Report

Task ID: `TASK_ASO_S1_180_STAGE1_REGRESSION_RELEASE_GATE`

Agent instance: `implementation_aso_s1_180_001`

Branch: `correction/aso-stage1-defect-remediation-v3.8.0`

Validation date: `2026-05-31`

Base evidence HEAD before release evidence files:
`5e90edffdba8872543ce663f2ffb4cefab8e21e5`

## Scope

This report records the Stage 1 final local regression gate. The gate covers
source tests, package-mode diagnostics, installed package smoke tests,
generated workspace smoke tests, lifecycle finalization, audit/correction
routing, state reconciliation, reporting, and package build behavior.

Remote GitHub Actions evidence for the eventual S1_180 pushed commit is selected
by `agent-system/11_release/REMOTE_CI_EVIDENCE.md` after the orchestrator
commits and pushes this task.

## Required Commands

| Command | Result | Evidence |
| --- | --- | --- |
| `git status --short --branch` | passed | Initial implementation attempt reported five new S1_180 release evidence files as intent-to-add changes on `correction/aso-stage1-defect-remediation-v3.8.0`; audit correction 001 adds README/schema-doc sync, packaged resource manifest, and focused test changes listed below. |
| `git diff --check` | passed | Whitespace check passed before and after generated build cleanup. |
| `PYTHONDONTWRITEBYTECODE=1 make test` | passed after generated-cache cleanup and correction coverage expansion | Initial S1_180 gate run: source hygiene passed; 605 ASO tests passed in 427.168s; 6 top-level tests passed in 0.696s. Correction 002 rerun: source hygiene passed; 606 ASO tests passed in 408.380s; 6 top-level tests passed in 0.687s. |
| `PYTHONDONTWRITEBYTECODE=1 make smoke` | passed | Package lint/doctor/layout, design/context/rules/state/plan/dashboard/checkpoint, and governance smoke passed; `SMOKE_RESULT: passed (18 assertions)`; log size 6,481 bytes. |
| `PYTHONDONTWRITEBYTECODE=1 make doctor` | passed | `ASO doctor: PASSED`; 0 errors, 0 warnings, 0 info, 0 findings; log size 200 bytes. |
| `PYTHONDONTWRITEBYTECODE=1 make lint` | passed | `ASO lint: PASSED`; 0 errors, 0 warnings, 0 info, 0 findings; log size 196 bytes. |
| `PYTHONDONTWRITEBYTECODE=1 make install-smoke` | passed | Clean source install, installed CLI smoke, wheel install smoke, and sdist install smoke passed from temporary directories; log size 559,004 bytes. |
| `PYTHONDONTWRITEBYTECODE=1 make install-test-smoke` | passed | Clean install with `[test]` extra passed; installed CLI/project smoke passed; `jsonschema 4.26.0` verified; log size 4,825 bytes. |
| `PYTHONDONTWRITEBYTECODE=1 make e2e-real-tz-smoke` | passed | 2 real-TZ filesystem/governance lifecycle smoke tests passed in 35.587s; log size 555 bytes. |
| `PYTHONDONTWRITEBYTECODE=1 make ci` | passed | Repeated source tests, smoke, doctor, lint, install-smoke, install-test-smoke, real-TZ smoke, source-contamination guard, and `git diff --check`; log size 572,939 bytes. |
| `python3 -m build` | passed after build frontend bootstrap | Initial exact command failed because base Python lacked `build`; `python3 -m pip install --user build` was blocked by PEP 668; `python3 -m pip install --user --break-system-packages build` installed `build 1.5.0`; rerun exact `python3 -m build` built `agent_system_orchestrator-3.8.0.tar.gz` and `agent_system_orchestrator-3.8.0-py3-none-any.whl`; log size 549,562 bytes. |

## Additional Checks

| Command | Result | Evidence |
| --- | --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py package-layout verify --root . --mode package --strict` | passed | `ASO package-layout verify: PASSED`; 0 findings. |
| `PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py package-sync verify --root . --mode package --strict` | failed as unsupported invocation | `package-sync verify` is a compatibility alias and does not accept `--mode package`; command exited with argparse usage error. |
| `PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py package-sync verify --root . --strict` | passed | Supported strict alias form passed with 0 findings. |
| `PYTHONDONTWRITEBYTECODE=1 bash agent-system/scripts/source_hygiene.sh` after cleanup | passed | Generated `dist/` and `agent_system_orchestrator.egg-info` from `python3 -m build` were removed; source hygiene passed. |
| `git status --short --branch --untracked-files=all` after cleanup | passed | Initial implementation attempt reported the five S1_180 release evidence files as intent-to-add changes; audit correction 001 extends the dirty tree with bounded schema-doc sync files. |

## Audit Correction 001

`AUDIT_ASO_S1_180_STAGE1_REGRESSION_RELEASE_GATE` attempt 001 failed D18 because
the source `agent-system/README.md` and packaged resource
`agent-system/README.md` still carried stale duplicate-contract authority
wording instead of the active Runtime Schema `3.2.0` closure text. Correction
agent `implementation_aso_s1_180_correction_001` updates both README surfaces
to Runtime Schema `3.2.0`; no duplicate `3_2_0` contract file is
authoritative, refreshes the packaged resource manifest hash, and expands
`test_scope_terminology_release_evidence.py` so root, governance, packaged
README, and S1_180 release-evidence contract-authority wording stay
synchronized.

The corrected dirty tree is expected to contain the five release evidence files
from attempt 001 plus:

```text
agent-system/README.md
agent-system/tools/aso/agent_system_orchestrator_aso/resources/RESOURCE_MANIFEST.json
agent-system/tools/aso/agent_system_orchestrator_aso/resources/agent-system/README.md
agent-system/tools/aso/tests/test_scope_terminology_release_evidence.py
```

## Generated Output Cleanup

`python3 -m build` created generated package artifacts under `dist/` and
`agent-system/tools/aso/agent_system_orchestrator.egg-info/`. They were removed
after the build passed. No generated/local roots are intended for commit.

The first `make test` attempt failed before tests because earlier diagnostic
Python imports created generated `__pycache__` files under
`agent-system/tools/aso/**`. Only those generated cache artifacts were removed,
`source_hygiene.sh` passed, and the required command was rerun successfully.

## Output Size Summary

Final passed required-command logs under `/tmp/aso_s1_180_gate_logs` totaled
1,694,785 bytes. The largest outputs were packaging/build steps:

| Log | Bytes |
| --- | ---: |
| `make-install-smoke.log` | 559,004 |
| `make-ci.log` | 572,939 |
| `python-build.log` | 549,562 |
| `make-smoke.log` | 6,481 |
| `make-install-test-smoke.log` | 4,825 |
| `make-test.log` | 1,023 |
| `make-e2e-real-tz-smoke.log` | 555 |
| `make-doctor.log` | 200 |
| `make-lint.log` | 196 |

ASO-controlled diagnostic/reporting commands are compact. External packaging
and build frontends remain verbose and are captured as release-gate log output.

## Gate Interpretation

The implementation agent may report local command outcomes, but final pass/fail
authority belongs to the fresh tester and auditor agents for
`TEST_ASO_S1_180_STAGE1_REGRESSION_RELEASE_GATE` and
`AUDIT_ASO_S1_180_STAGE1_REGRESSION_RELEASE_GATE`.

The release gate must not claim full automatic product generation. The
`e2e-real-tz-smoke` target is a filesystem/governance lifecycle smoke and not a
live runner or product acceptance gate.
