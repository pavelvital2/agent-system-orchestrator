# ASO Stage 1 Defect Remediation v3.8.0 Release Notes

Task ID: `TASK_ASO_S1_180_STAGE1_REGRESSION_RELEASE_GATE`

Branch: `correction/aso-stage1-defect-remediation-v3.8.0`

Base evidence HEAD for this release gate:
`5e90edffdba8872543ce663f2ffb4cefab8e21e5`

Validation date: `2026-05-31`

## Version Tuple

```text
CURRENT_PACKAGE_VERSION: 3.8.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.8.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.2.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
```

Runtime Schema `3.2.0` continues to use the packaged
`runtime_state_3_1_0.contract.json` contract file as the synchronized active
runtime-state contract. No duplicate `3_2_0` contract file is authoritative.

## Release Scope

Stage 1 turns the ASO governance/control-plane into a coherent terminal,
observable, reproducible lifecycle/state machine before Stage 2 automation is
attempted. The release covers source CLI checks, installed package checks,
generated workspace checks, lifecycle finalization, audit/correction routing,
state reconciliation, reporting, and packaging gates.

This release does not implement a live runner, autonomous external-worker
dispatch, daemon mode, ASO Studio, a secret collector, or a full automatic
product generator.

## Defect Closure Summary

| Defect | Stage 1 closure evidence |
| --- | --- |
| D01 | `PROJECT_COMPLETED`, `FINAL_CHECKPOINT_COMPLETE`, `NO_NEXT_ACTION`, and `aso lifecycle finalize` are implemented and covered by lifecycle finalization tests. |
| D02 | Routing authority is centralized through the transition engine and exercised by plan-next, state verify, lifecycle, and audit/correction tests. |
| D03 | `NEXT_ACTION` is derived or verified against canonical transition state, with stale cache detection in next-action and state verification tests. |
| D04 | Structured lifecycle mutation and state reconciliation replace append-only-only drift paths, covered by lifecycle/state reconcile tests. |
| D05 | Result-only and artifact-package lifecycle modes are separated, with result-only audit routing not requiring synthetic artifact acceptance. |
| D06 | Audit markdown results produce governed `AUDIT_RESULT_RECEIPT` records without forcing P5 artifact-package acceptance. |
| D07 | Shared RESULT parsing is used by record-result, lifecycle, audit, correction, and checkpoint flows. |
| D08 | Canonical `manifest.json` is enforced while legacy `artifact_package_manifest.json` candidates migrate with warnings and tests. |
| D09 | Failed audits route to `CORRECTION_REQUIRED`; checkpoint and terminal routes are blocked while effective audit failure remains unresolved. |
| D10 | Correction resolution graph fields `correction_of`, `resolved_by`, `superseded_by`, and `effective_status` drive effective-state rollups. |
| D11 | Source-boundary severity tiers SB0-SB4 are defined and enforced with allowed own handoff, prompt, task, and dispatch context. |
| D12 | Routine context is minimized through a whitelist, broad corpus rejection, and compact handoff context policy. |
| D13 | Role output skeletons, checklists, and self-validation make machine-invalid role outputs correction-visible before RESULT acceptance. |
| D14 | State sidecars are reconciled through structured commands and deterministic receipts instead of manual line patching. |
| D15 | Operator event logs, compact operator report generation, and final-run receipt generation are implemented and tested. |
| D16 | Compact stdout and diff-to-file behavior are covered by compact status, operator report, and state reconcile tests. |
| D17 | Bootstrap materialization writes mandatory state views and validates startup/render consistency. |
| D18 | Canonical enum registry, schema coherence, dispatch-role checks, README/schema-contract wording (Runtime Schema `3.2.0`; no duplicate `3_2_0` contract file is authoritative), packaged resource mirror sync, and version synchronization cover known enum/schema drift. |
| D19 | ASO-managed checkpoint evidence policy preserves clean package freeze points and blocks force-added runtime checkpoint evidence. |
| D20 | Clean install, installed CLI smoke, install-test smoke, package layout, and generated workspace checks cover installer/dependency readiness for Stage 1. |

No D01-D20 defect is intentionally deferred inside Stage 1. Stage 2 work is
limited to the follow-up areas listed in
`agent-system/11_release/STAGE2_READINESS_HANDOFF.md`.

## Release Evidence Files

```text
agent-system/11_release/ASO_STAGE1_DEFECT_REMEDIATION_V3_8_0_RELEASE_NOTES.md
agent-system/11_release/VALIDATION_REPORT.md
agent-system/11_release/REGRESSION_SUMMARY.md
agent-system/11_release/REMOTE_CI_EVIDENCE.md
agent-system/11_release/STAGE2_READINESS_HANDOFF.md
```

Local validation details are recorded in `VALIDATION_REPORT.md`. Baseline to
final metric comparison is recorded in `REGRESSION_SUMMARY.md`. Remote CI is
recorded as a final-pushed-head selector/procedure because the implementation
agent must not commit or push this task.

## Audit Correction 001

`AUDIT_ASO_S1_180_STAGE1_REGRESSION_RELEASE_GATE` attempt 001 failed because
`agent-system/README.md` and the packaged resource mirror still carried stale
duplicate-contract authority wording instead of the active Runtime Schema
`3.2.0` closure text. Correction
`TASK_ASO_S1_180_CORRECTION_SCHEMA_DOC_SYNC` changes those surfaces to Runtime
Schema `3.2.0`; no duplicate `3_2_0` contract file is authoritative,
updates the packaged resource manifest hash, and extends
release-evidence/version coherence coverage to the source README, packaged
resource README, and S1_180 release evidence docs.
