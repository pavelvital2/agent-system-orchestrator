# ASO Stage 1 Baseline Metrics

Task ID: `TASK_ASO_S1_010_BASELINE_METRICS_AND_REPRODUCTION`

Generated at UTC: `2026-05-28T18:56:11Z`

Baseline branch: `correction/aso-stage1-defect-remediation-v3.8.0`

Baseline source head: `903e8a8946da95e784931f6610391ec33fd12733`

This file freezes the v3.7.9 baseline for Stage 1 defect remediation. It is
evidence only. No runtime code, tests, Makefile target, installer behavior, or
public CLI behavior is changed by this task.

Machine-readable evidence is in
`agent-system/11_release/ASO_STAGE1_BASELINE_METRICS.json`.

## Version Tuple

| Field | Value |
| --- | --- |
| Package version | `3.7.9` |
| Governance ruleset version | `3.7.9` |
| Runtime schema version | `3.1.1` |
| Artifact package schema version | `1.1.0` |

## Numeric Metrics

| Metric | Before Stage 1 | After Task 010 |
| --- | ---: | ---: |
| ASO top-level CLI commands | 27 | 27 |
| ASO command leaves including subcommands | 59 | 59 |
| Allowed lifecycle events | 10 | 10 |
| State transition sources | 7 | 7 |
| State transition edges | 8 | 8 |
| Terminal states in runtime contract | 1 | 1 |
| Release evidence files added by this task | 0 | 2 |
| Runtime behavior files changed by this task | 0 | 0 |
| Known Stage 1 defects tracked | 20 | 20 |
| Defects reproduced in baseline | 11 | 11 |
| Defects already fixed in baseline | 7 | 7 |
| Defects blocked by missing environment evidence | 2 | 2 |
| Defects closed by Task 010 | 0 | 0 |
| Unresolved findings | 13 | 13 |

## Terminal-State Status

| Check | Baseline result |
| --- | --- |
| Runtime terminal states | `CHECKPOINT_ELIGIBLE` only |
| `PROJECT_COMPLETED` state available | no |
| `FINAL_CHECKPOINT_COMPLETE` state available | no |
| `NO_NEXT_ACTION` available | no |
| `aso lifecycle finalize` command available | no |
| Project-completion terminal reached | no |

Evidence:

- `agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json`
- `PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lifecycle --help`
- `agent-system/tools/aso/tests/test_lifecycle_state_reconciliation.py::test_full_auditor_pass_lifecycle_keeps_checkpoint_route_after_auditor_routing`

## Validation Results

| Command | Result | Evidence summary |
| --- | --- | --- |
| `git status --short --branch` | passed | Clean worktree before evidence edits on `correction/aso-stage1-defect-remediation-v3.8.0`. |
| `python3 -m pip install -e ".[test]"` | failed | System Python refused the install with PEP 668 `externally-managed-environment`. |
| `PYTHONDONTWRITEBYTECODE=1 make source-contamination-guard` | passed after cleanup | Initial run found ignored bytecode cache artifacts; cleanup removed only `__pycache__`/`*.pyc` under ASO package/test paths, then the guard passed. |
| `PYTHONDONTWRITEBYTECODE=1 make install-smoke` | passed | Clean source install, installed CLI smoke, wheel install smoke, and sdist install smoke passed from temporary directories. |
| `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s agent-system/tools/aso/tests -v` | passed | 497 tests passed in 295.060s. |
| `PYTHONDONTWRITEBYTECODE=1 make test` | passed | Source hygiene passed; 497 ASO tests passed in 289.560s; 6 top-level tests passed in 0.600s. |
| `PYTHONDONTWRITEBYTECODE=1 make smoke` | passed | Package status/lint/doctor/layout, design/context/rules/state/plan/dashboard/checkpoint, and governance smoke passed; `SMOKE_RESULT: passed (18 assertions)`. |
| `PYTHONDONTWRITEBYTECODE=1 make doctor` | passed | 0 errors, 0 warnings, 0 info, 0 findings. |

The editable install failure is an environment result for the exact required
command, not a package build result. The isolated install smoke verifies clean
source, wheel, and sdist install paths.

## Output And Diff Estimates

| Metric | Estimate |
| --- | ---: |
| Required gate stdout, excluding install-smoke | 70,200 bytes |
| `make install-smoke` stdout | 550,000 bytes |
| All baseline validation stdout | 620,200 bytes |
| Pre-task diff files | 0 |
| Pre-task diff bytes | 0 |
| Runtime behavior diff files from Task 010 | 0 |
| Task 010 release evidence diff bytes | 27,889 |

The stdout estimates are numeric but approximate because logs were not persisted
as release artifacts. The installed-package smoke output was large enough to be
truncated by the execution tool, which is recorded as D16 baseline evidence.

## Defect Baseline

| ID | Status | Evidence |
| --- | --- | --- |
| D01 | reproduced | Runtime contract terminal states contain only `CHECKPOINT_ELIGIBLE`; `lifecycle --help` has no `finalize`; lifecycle reconciliation test keeps checkpoint route after auditor pass. |
| D02 | reproduced | Read-only source inventory found routing/action literals in multiple command modules; transition engine tests exist but do not prove exclusive authority. |
| D03 | reproduced | Stale `NEXT_ACTION` is reproduced by lifecycle/state tests and detected by transition/state verification guards. |
| D04 | reproduced | Manual lifecycle events can diverge from materialized sidecars; confirmed receive-result materialization covers only structured command path. |
| D05 | reproduced | Profile pass still requires accepted result-package bookkeeping before audit route; termination requires artifact accepted receipt. |
| D06 | already fixed | `AUDIT_RESULT_RECEIPT` is emitted and tested for failed-audit lifecycle. |
| D07 | already fixed | Shared RESULT parser coverage exists in `test_result_parser.py` and record-result tests. |
| D08 | already fixed | Canonical `manifest.json` plus legacy alias migration is covered by artifact manifest contract tests. |
| D09 | already fixed | Audit fail routes to `CORRECTION_REQUIRED` and blocks checkpoint in record-result, plan-next, and checkpoint tests. |
| D10 | reproduced | `correction_of`, `resolved_by`, and `effective_status` were not found in active implementation; focused correction graph test is absent. |
| D11 | reproduced | SB0-SB4 severity tiers were not found; context guards remain coarse. |
| D12 | already fixed | Routine context policy and broad-corpus rejection are present and tested. |
| D13 | blocked by missing environment evidence | No live invalid role-output corpus is available; malformed parser fixtures do not prove real role-output failure. |
| D14 | reproduced | Manual sidecar/lifecycle drift remains reproducible, though structured render/materialization exists. |
| D15 | reproduced | Focused operator-reporting test/command is absent; release reports remain manual evidence files. |
| D16 | reproduced | Installed-package smoke emits large build/copy stdout; compact output and diff-to-file defaults are incomplete. |
| D17 | already fixed | State init/render/bootstrap materialization and install smoke paths are covered. |
| D18 | already fixed | Version coherence, runtime schema contracts, and task-kind guards pass. |
| D19 | blocked by missing environment evidence | Package checkpoint preflight passes, but no live checkpoint evidence conflict was available; focused evidence-selection test is absent. |
| D20 | reproduced | Exact editable install command fails under PEP 668, while isolated clean/wheel/sdist install smoke passes. |

Status counts:

- reproduced: 11
- already fixed: 7
- not reproducible: 0
- blocked by missing environment evidence: 2

## Unresolved Findings

- D01: terminal project completion is missing.
- D02: transition-engine authority is not proven across every routing command.
- D03: `NEXT_ACTION` can still be stale, although guards detect it.
- D04: append-only lifecycle logs can diverge from materialized state.
- D05: result-only lifecycle mode is not separated from artifact-package lifecycle.
- D10: effective correction-resolution graph is missing.
- D11: source-boundary severity tiers SB0-SB4 are missing.
- D13: real role-output invalidity needs live environment evidence.
- D14: manual sidecar drift remains reproducible.
- D15: operator report/final receipt automation is missing.
- D16: stdout and build output remain noisy.
- D19: checkpoint evidence conflict needs live workspace evidence.
- D20: exact editable install is blocked by PEP 668 in this environment.

## Scope Notes

Task 010 closes no defects and implements no Stage 2 functionality. It adds no
live runner automation, autonomous external-worker dispatch, daemon mode, ASO
Studio UI, secret collector, or automatic product generator.
