# ASO Stage 1 Defect Remediation v3.8.0 Regression Summary

Task ID: `TASK_ASO_S1_180_STAGE1_REGRESSION_RELEASE_GATE`

Validation date: `2026-05-31`

Baseline evidence:
`agent-system/11_release/ASO_STAGE1_BASELINE_METRICS.md`

## Baseline To Final Metrics

| Metric | Stage 1 baseline | Stage 1 final evidence |
| --- | --- | --- |
| Correction loops / unresolved findings | 13 unresolved findings across D01, D02, D03, D04, D05, D10, D11, D13, D14, D15, D16, D19, D20 | 0 unresolved D01-D20 findings in Stage 1 local evidence; audit/correction loops remain active only for unresolved effective failures. |
| Manual sidecar patches | Manual sidecar/report recovery and line-based JSON patching were reproducible risks | 0 runtime sidecar manual patches in the final gate; state mutation/reconcile/finalize/report paths are structured commands with receipts. S1_180 attempt 001 added five manual release evidence files; audit correction 001 adds only schema-doc sync, packaged resource manifest, and focused test coverage. |
| Stale state findings | Stale `NEXT_ACTION` and lifecycle/sidecar drift were reproducible | `make smoke`, `make doctor`, `make lint`, and `make ci` passed with 0 package findings; state verify/reconcile tests cover stale state detection and repair. |
| Stdout size | Baseline estimated about 620,200 bytes for required validation, with install smoke output large enough to be truncated by the execution tool | Final passed required-command logs totaled 1,694,785 bytes because the final gate includes aggregate `make ci` plus exact `python3 -m build`; ASO diagnostic outputs are compact, while pip/build packaging output remains verbose. |
| Terminal route success | No true project-completed terminal route; `CHECKPOINT_ELIGIBLE` was the only terminal state | True terminal route implemented and tested: `FINAL_CHECKPOINT_COMPLETE` to `PROJECT_COMPLETED` to `NO_NEXT_ACTION`; terminal states are `PROJECT_COMPLETED` and `NO_NEXT_ACTION`. |
| Report completeness | Operator report/final receipt automation was absent | Operator event log, compact report, and final-run receipt tests are included in the 606-test ASO source suite; the prior full `make ci` gate repeated 605 plus 6 before correction 002 added release-evidence wording coverage. |
| Tests passed | Baseline `make test`: 497 ASO tests plus 6 top-level tests | Final correction `make test`: 606 ASO tests plus 6 top-level tests; prior full `make ci` repeated 605 plus 6 and also ran 2 real-TZ smoke tests before correction 002 added the focused release-evidence coverage. |

## D01-D20 Regression Closure

| Defect | Baseline status | Final status |
| --- | --- | --- |
| D01 | reproduced | Closed by lifecycle finalization terminal route evidence. |
| D02 | reproduced | Closed by transition-engine authority evidence. |
| D03 | reproduced | Closed by derived next-action/cache verification evidence. |
| D04 | reproduced | Closed by transactional lifecycle/state reconciliation evidence. |
| D05 | reproduced | Closed by result-only versus artifact-package lifecycle evidence. |
| D06 | already fixed | Preserved by audit result receipt evidence. |
| D07 | already fixed | Preserved by shared RESULT parser evidence. |
| D08 | already fixed | Preserved and expanded by manifest migration evidence. |
| D09 | already fixed | Preserved and expanded by audit fail correction routing evidence. |
| D10 | reproduced | Closed by effective correction-resolution graph evidence. |
| D11 | reproduced | Closed by SB0-SB4 source-boundary severity evidence. |
| D12 | already fixed | Preserved by context minimization/budget evidence. |
| D13 | blocked by missing environment evidence | Closed by role-output contract and self-validation fixtures. |
| D14 | reproduced | Closed by structured state reconcile and receipt evidence. |
| D15 | reproduced | Closed by operator event log, compact report, and final receipt evidence. |
| D16 | reproduced | Closed by compact stdout and diff-to-file regression evidence. |
| D17 | already fixed | Preserved and expanded by bootstrap materialization evidence. |
| D18 | already fixed | Preserved by enum/schema/version coherence evidence, including synchronized Runtime Schema `3.2.0`; no duplicate `3_2_0` contract file is authoritative wording in root, governance, packaged README, and S1_180 release-evidence surfaces. |
| D19 | blocked by missing environment evidence | Closed by checkpoint evidence selection and checkpoint policy fixtures. |
| D20 | reproduced | Closed for Stage 1 by clean install, package layout, installed CLI, and generated workspace smoke evidence. |

No Stage 1 D01-D20 defect remains explicitly deferred. Stage 2 scope is not
included in this closure statement.

## Stage 2 Boundary

The final Stage 1 evidence does not assert automatic product creation. Runner
adapter integration, GUI/monitoring UI, one-click install UX, product quality
profiles expansion, and live agent automation remain Stage 2 or later work.
