# ASO Workspace Bootstrap Runtime Lifecycle P4.1 v3.6.1 Validation Report

```text
REPORT_ID: ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_VALIDATION_REPORT
TASK_ID: HFX_P41_080
AGENT_INSTANCE_ID: HFX_P41_080_PROFILE_AGENT_20260522
AGENT_ROLE: release_manager
DATE: 2026-05-22
BRANCH: hotfix/workspace-bootstrap-runtime-lifecycle-p4.1-v3.6.1
VALIDATION_HEAD_BEFORE_REPORT: 563be1e21555a5cb8e59a27c3f764f5f134feda5
PACKAGE_VERSION: 3.6.1
GOVERNANCE_RULESET_VERSION: 3.6.1
RUNTIME_SCHEMA_VERSION: 3.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
VALIDATION_STATUS: passed
FINAL_REPORT_COMMIT_PENDING: no
FINAL_CLEANUP_PENDING: no
FINAL_PUSH_CLAIMED: no
```

## Summary

P4.1 local validation passed. The hotfix preserves Runtime Schema `3.1.0` and
the corrected P4 designer-led authority boundary while fixing the three
reported bootstrap/runtime lifecycle incidents:

- package-mode checks no longer produce package-layout blockers for workspace
  roots without first reporting the mode mismatch;
- JSON-only Runtime Schema `3.1.0` sidecars can be rendered into derived
  Markdown compatibility views;
- profile-agent RESULT artifacts require a termination lifecycle event before
  audit route.

ASO remains a deterministic governance/control conveyor. It does not read raw
TZ by meaning, replace project designer or requirements analyst reasoning,
generate owner questions from TZ, run a daemon, dispatch live agents, execute
checkpoints, generate products, collect secrets, or run external workers.

## Branch Evidence

```text
COMMAND: git branch --show-current
EXIT_CODE: 0
OUTPUT: hotfix/workspace-bootstrap-runtime-lifecycle-p4.1-v3.6.1

COMMAND: git rev-parse HEAD
EXIT_CODE: 0
OUTPUT: 563be1e21555a5cb8e59a27c3f764f5f134feda5
```

Task commit list before this report:

```text
563be1e test(hotfix): cover lifecycle negative guards
93a3725 fix(hotfix): integrate bootstrap workspace checks
c82fe00 fix(hotfix): add incident repair hints
ce1d066 fix(hotfix): record agent termination lifecycle events
a2b7df0 fix(hotfix): materialize runtime markdown views
8c163b1 fix(hotfix): guard package mode against workspace roots
39b59c2 chore(hotfix): define p4.1 version boundary
```

## Command Evidence

```text
COMMAND: make test
EXIT_CODE: 0
OUTCOME: passed; source hygiene passed, 276 ASO tool tests passed, and 5 agent-system tests passed.

COMMAND: make smoke
EXIT_CODE: 0
OUTCOME: passed; package status, strict lint, strict doctor, package-layout, validators, state verify/render, plan-next, dashboard, checkpoint-preflight, and governance smoke passed.
GOVERNANCE_SMOKE_RESULT: passed (18 assertions), including active 3.6.1 package/governance with runtime schema 3.1.0.

COMMAND: bash install.sh
EXIT_CODE: 0
OUTCOME: passed; editable install completed and package-layout verification passed.
INSTALLED_PACKAGE: agent-system-orchestrator 3.6.1

COMMAND: make verify-install
EXIT_CODE: 0
OUTCOME: passed; installed `.venv/bin/aso` help, package status, Project Factory help, strict lint, strict doctor, and package-layout verification passed.

COMMAND: python3 agent-system/tools/aso/aso.py status --root . --mode package
EXIT_CODE: 0
OUTCOME: passed; package status check completed for package mode.

COMMAND: python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; errors 0, warnings 0, findings 0.

COMMAND: python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; errors 0, warnings 0, findings 0.

COMMAND: python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
EXIT_CODE: 0
OUTCOME: passed; canonical package source and package entrypoint checks passed.

COMMAND: python3 agent-system/tools/aso/aso.py checkpoint-preflight --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; ELIGIBLE dry-run/read-only, blocking rules 0.

COMMAND: git diff --check
EXIT_CODE: 0
OUTCOME: passed; no whitespace errors.

COMMAND: git ls-files project-input project-runtime project-archive .venv
EXIT_CODE: 0
OUTPUT: empty
OUTCOME: passed; no forbidden local input/runtime/archive/venv roots are tracked for publication.
```

## Incident Replay Evidence

Incident replay details are recorded in
`agent-system/11_release/ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_INCIDENT_REPLAY_NOTES.md`.

The covered replay surfaces are:

- generated workspace checked in workspace mode;
- generated workspace incorrectly checked in package mode;
- JSON-only runtime state before materialization;
- JSON state after Markdown materialization;
- RESULT without termination event;
- RESULT with valid termination event.

## Cleanup Evidence

The publication-boundary check passed:

```text
COMMAND: git ls-files project-input project-runtime project-archive .venv
EXIT_CODE: 0
OUTPUT: empty
```

The following local cleanup was performed before final commit/push by the
orchestrator:

```bash
rm -rf project-input/aso_hotfix_workspace_bootstrap_runtime_lifecycle_p4_1_v3_6_1
rm -rf .venv
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
git status --short --branch
git ls-files project-input project-runtime project-archive .venv
```

Expected tracked-file result after cleanup remains empty.

## Release Readiness Notes

The HFX_P41_080 release docs are ready for the final orchestrator-owned commit
and push after audit acceptance. No tag, merge, or release publication is
performed by this report.
