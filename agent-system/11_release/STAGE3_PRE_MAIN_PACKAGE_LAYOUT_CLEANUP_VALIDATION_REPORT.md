# Stage 3 Pre-Main Package Layout Cleanup Validation Report

```text
REPORT_ID: STAGE3_PRE_MAIN_PACKAGE_LAYOUT_CLEANUP_VALIDATION_REPORT
TASK_ID: TASK_ASO_PRE_MAIN_006A_FINAL_VALIDATION_BLOCKER_FIX
AGENT_INSTANCE_ID: TASK_ASO_PRE_MAIN_006A_FINAL_VALIDATION_BLOCKER_FIX_PROFILE_AGENT_20260520
DATE: 2026-05-20
BRANCH: upgrade/stage-3-pre-main-package-layout-cleanup
FINAL_COMMIT_PENDING: yes
REMOTE_HEAD_VERIFICATION_REQUIRED_AFTER_ORCHESTRATOR_PUSH: yes
REMOTE_CI_CLAIMED: no
MAIN_MERGE_CLAIMED: no
PACKAGE_VERSION: 3.1.2
GOVERNANCE_RULESET_VERSION: 3.1.2
RUNTIME_SCHEMA_VERSION: 3.0.0
CANONICAL_PACKAGE_SOURCE: agent-system/tools/aso/agent_system_orchestrator_aso/
ROOT_DUPLICATE_PACKAGE_TRACKED: no
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
VALIDATION_STATUS: passed-local
BLOCKER_FIXED: yes
```

## Package Layout

The canonical installable ASO package source is:

```text
agent-system/tools/aso/agent_system_orchestrator_aso/
```

The removed duplicate root package path is:

```text
agent_system_orchestrator_aso/
```

Package discovery is configured through `pyproject.toml` with:

```text
[tool.setuptools.packages.find]
where = ["agent-system/tools/aso"]
include = ["agent_system_orchestrator_aso*"]
```

## Correction Summary

```text
1. Updated agent-system/tools/aso/tests/test_packaging.py so the active package version guard is 3.1.2 and the __version__ assertion is derived from pyproject metadata.
2. Updated the final source archive hygiene command to reject only root project-input/, root project-runtime/, root project-archive/, root agent_system_orchestrator_aso/, pycache directories, and pyc/pyo artifacts.
3. Preserved intentional tracked nested fixtures under agent-system/tests/fixtures/state/*/project-runtime/.
```

## Command Evidence

```text
COMMAND: git status --short --branch
EXIT_CODE: 0
OUTCOME: passed; branch is upgrade/stage-3-pre-main-package-layout-cleanup; tracked local modified files were the validation report and packaging test. The final validation commands doc is under ignored root project-input/ and is intentionally not listed by git status.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest agent-system/tools/aso/tests/test_packaging.py
EXIT_CODE: 0
OUTCOME: passed; 5 tests ran successfully.

COMMAND: PYTHONDONTWRITEBYTECODE=1 make ci
EXIT_CODE: 0
OUTCOME: passed; source_hygiene passed; 119 ASO tool tests passed; 5 agent-system tests passed; package status/lint/doctor/package-layout checks passed; validate-design, validate-context-pack, validate-rules, state verify, plan-next, dashboard, checkpoint-preflight, governance smoke tests, doctor, lint, and git diff --check passed.

COMMAND: git archive --format=tar HEAD > /tmp/aso-pre-main-source.tar; if tar -tf /tmp/aso-pre-main-source.tar | grep -E '^project-input/|^project-runtime/|^project-archive/|(^|/)__pycache__/|\.py[co]$|^agent_system_orchestrator_aso/'; then echo "source archive hygiene failed"; rm -f /tmp/aso-pre-main-source.tar; exit 1; fi; rm -f /tmp/aso-pre-main-source.tar
EXIT_CODE: 0
OUTCOME: passed; no forbidden root generated roots, root duplicate package, pycache directories, or pyc/pyo artifacts were found in the source archive.

COMMAND: git diff --check
EXIT_CODE: 0
OUTCOME: passed; no whitespace errors reported.

COMMAND: git ls-files project-input project-runtime project-archive agent_system_orchestrator_aso '*__pycache__*' '*.pyc' '*.pyo'
EXIT_CODE: 0
OUTCOME: passed; output empty.
```

## Acceptance Criteria Status

```text
Branch: pass; validation ran on upgrade/stage-3-pre-main-package-layout-cleanup.
Version tuple: pass; packaging test now confirms pyproject version 3.1.2 and package __version__ coherence.
Root duplicate package: pass; agent_system_orchestrator_aso/ tracked output is empty.
Canonical ASO package: pass; make ci package-layout verification confirmed agent-system/tools/aso/agent_system_orchestrator_aso/.
Make targets: pass; make ci completed successfully.
Tracked hygiene: pass; root project-input, project-runtime, project-archive, root duplicate package, pycache, pyc, and pyo tracked output is empty.
Source archive hygiene: pass; corrected command rejects forbidden root paths while allowing intentional nested state fixtures.
Merge readiness: local validation unblocked only; no merge to main performed.
Checkpoint policy: no commit or push by this validation agent.
```

## Forbidden Root Evidence

```text
git ls-files project-input project-runtime project-archive agent_system_orchestrator_aso '*__pycache__*' '*.pyc' '*.pyo': exit 0, output empty
corrected source archive hygiene command: exit 0, output empty
```

## Merge Readiness

This local blocker-fix validation unblocks the final validation commands that
previously failed on the stale `3.1.1` packaging assertion and over-broad source
archive hygiene pattern. This report does not claim a merge to `main`, does not
claim a final commit hash, and does not claim remote CI success. Those remain
orchestrator-owned post-push checks.

## Limitations And Follow-Up Risks

```text
1. Changes are local and uncommitted by instruction; final commit and push remain orchestrator-owned.
2. Remote HEAD verification and GitHub Actions success cannot be claimed before orchestrator push.
3. git archive validation used HEAD, which is appropriate for tracked source archive hygiene; uncommitted documentation/test corrections still require orchestrator commit before remote validation.
```
