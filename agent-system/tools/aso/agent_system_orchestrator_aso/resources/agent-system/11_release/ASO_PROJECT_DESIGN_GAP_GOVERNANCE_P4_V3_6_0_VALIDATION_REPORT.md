# ASO Project Design Gap Governance P4 v3.6.0 Validation Report

```text
REPORT_ID: ASO_PROJECT_DESIGN_GAP_GOVERNANCE_P4_V3_6_0_VALIDATION_REPORT
TASK_ID: TASK_ASO_DG4_100_DOCS_RELEASE_FINAL_VALIDATION_CLEANUP
AGENT_INSTANCE_ID: TASK_ASO_DG4_100_PROFILE_AGENT_20260522
AGENT_ROLE: release_manager
DATE: 2026-05-22
BRANCH: upgrade/project-design-gap-governance-p4-v3.6.0
VALIDATION_HEAD_BEFORE_REPORT: b6db34ebebe4712b160abd1a88c3950c477bcad2
BASE_COMMIT: b6349b965b89f0b096f06c07b0f1f780a41346aa
SUPERSEDED_BRANCH_LEFT_UNTOUCHED: upgrade/product-intake-capability-p4-v3.6.0
PACKAGE_VERSION: 3.6.0
GOVERNANCE_RULESET_VERSION: 3.6.0
RUNTIME_SCHEMA_VERSION: 3.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
VALIDATION_STATUS: passed
FINAL_REPORT_COMMIT_PENDING: yes
```

## Summary

Corrected P4 local validation passed. The branch is a descendant of the accepted
P3 base commit, the superseded product-intake P4 branch was not merged or
altered, Runtime Schema remains `3.1.0`, and P4 remains designer-led. ASO is a
governance/control conveyor that validates artifacts, gates stage transitions,
routes existing audited owner-question cards, and records process evidence. ASO
does not semantically read TZ, generate product questions from TZ content,
replace project designer or requirements analyst reasoning, or ask owners to
make implementation technology choices.

Validation logs were captured under:

```text
/tmp/aso-dg4-100-validation-20260522-092743/
```

## Branch And Base Evidence

```text
COMMAND: git rev-parse --abbrev-ref HEAD
EXIT_CODE: 0
OUTPUT: upgrade/project-design-gap-governance-p4-v3.6.0

COMMAND: git rev-parse HEAD
EXIT_CODE: 0
OUTPUT: b6db34ebebe4712b160abd1a88c3950c477bcad2

COMMAND: git merge-base --is-ancestor b6349b965b89f0b096f06c07b0f1f780a41346aa HEAD
EXIT_CODE: 0
OUTCOME: passed; current branch is a descendant of the accepted P3 base.

COMMAND: git show-ref --verify refs/heads/upgrade/product-intake-capability-p4-v3.6.0
EXIT_CODE: 0
OUTPUT: 68ee16e188fd7f39963c1735891ce4e7de968e43 refs/heads/upgrade/product-intake-capability-p4-v3.6.0
OUTCOME: superseded branch still exists locally and was left untouched by this task.
```

## Baseline Validation Evidence

```text
COMMAND: make test
EXIT_CODE: 0
OUTCOME: passed; source hygiene passed, 265 ASO tool tests passed, and 5 agent-system tests passed.

COMMAND: make smoke
EXIT_CODE: 0
OUTCOME: passed; package status, strict lint, strict doctor, package-layout, validators, state verify/render, plan-next, dashboard, checkpoint-preflight, and governance smoke passed. Governance smoke result: passed, 18 assertions.

COMMAND: bash install.sh
EXIT_CODE: 0
OUTCOME: passed; editable install completed for agent-system-orchestrator 3.6.0 and package-layout verification passed.

COMMAND: make verify-install
EXIT_CODE: 0
OUTCOME: passed; installed `.venv/bin/aso` help, package status, Project Factory help, strict lint, strict doctor, and package-layout verification passed.

COMMAND: python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; errors 0, warnings 0, findings 0.

COMMAND: python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; errors 0, warnings 0, findings 0.

COMMAND: python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
EXIT_CODE: 0
OUTCOME: passed; canonical package path and root duplicate package check passed, findings 0.

COMMAND: python3 agent-system/tools/aso/aso.py checkpoint-preflight --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; ELIGIBLE dry-run/read-only, blocking rules 0, warnings 0.

COMMAND: git diff --check
EXIT_CODE: 0
OUTCOME: passed before report creation; no whitespace errors.
```

## Existing Surface Evidence

```text
COMMAND: python3 agent-system/tools/aso/aso.py state verify --root agent-system/tests/fixtures/state/valid_workspace --strict
EXIT_CODE: 0
OUTCOME: passed; findings 0.

COMMAND: python3 agent-system/tools/aso/aso.py propose next-task --root agent-system/tests/fixtures/state/valid_workspace --dry-run --json-out /tmp/aso-p3-next-task.json
EXIT_CODE: 0
OUTCOME: passed; proposal JSON was written under /tmp.

COMMAND: python3 agent-system/tools/aso/aso.py project create --local --engine-mode reference --target /tmp/aso-p4-reference --name "P4 Reference" --slug p4-reference --profile generic --repo-url none --branch main
EXIT_CODE: 0
OUTCOME: passed; Project Factory reference project was created under /tmp with package version 3.6.0 and runtime schema 3.1.0.

COMMAND: python3 agent-system/tools/aso/aso.py project verify-clean --root /tmp/aso-p4-reference --strict
EXIT_CODE: 0
OUTCOME: passed; lockfile and gitignore passed, tracked forbidden paths 0, nested Git paths 0, violations 0.

COMMAND: python3 agent-system/tools/aso/aso.py propose next-task --root agent-system/tests/fixtures/proposal_apply_p3/valid_workspace --dry-run --json-out /tmp/aso-dg4-apply-proposal.json
EXIT_CODE: 0
OUTCOME: passed; P3 proposal smoke remained functional.

COMMAND: python3 agent-system/tools/aso/aso.py apply --root agent-system/tests/fixtures/proposal_apply_p3/valid_workspace --proposal /tmp/aso-dg4-apply-proposal.json --dry-run --json-out /tmp/aso-dg4-apply-plan.json
EXIT_CODE: 0
OUTCOME: passed; P3 apply dry-run smoke remained functional.
```

## Corrected P4 Design/Gap Evidence

```text
COMMAND: python3 agent-system/tools/aso/aso.py design --help
EXIT_CODE: 0
OUTCOME: passed; design verify, questions, decision, and gate subcommands are exposed.

COMMAND: python3 agent-system/tools/aso/aso.py design verify --root agent-system/tests/fixtures/design_gap/valid_workspace --strict
EXIT_CODE: 0
OUTCOME: passed; errors 0, warnings 0, gap_registers 1, questions 1, answers 0.

COMMAND: python3 agent-system/tools/aso/aso.py design questions next --root agent-system/tests/fixtures/design_gap/valid_workspace --json-out /tmp/aso-dg4-next-question.json
EXIT_CODE: 0
OUTCOME: passed; selected existing audited question project-docs/design/questions/Q-001.json without generating question content.

COMMAND: python3 agent-system/tools/aso/aso.py design gate verify --root agent-system/tests/fixtures/design_gap/valid_workspace --stage DESIGN --strict
EXIT_CODE: 0
OUTCOME: passed; DESIGN stage gate passed with errors 0 and warnings 0.

COMMAND: python3 agent-system/tools/aso/aso.py design gate verify --root agent-system/tests/fixtures/design_gap/blocked_workspace --stage IMPLEMENTATION --strict
EXIT_CODE: 1
EXPECTED_FAILURE_STATUS: passed_expected_fail
OUTCOME: passed as negative guard; IMPLEMENTATION gate blocked on unanswered gap.
```

## Negative Guard Evidence

Each command below was expected to fail and did fail.

```text
COMMAND: python3 agent-system/tools/aso/aso.py design verify --root agent-system/tests/fixtures/design_gap/negative/technical_question --strict
EXIT_CODE: 1
EXPECTED_FAILURE_STATUS: passed_expected_fail
BLOCKER: DG4_QUESTION_008 Question contains technical implementation language.

COMMAND: python3 agent-system/tools/aso/aso.py design verify --root agent-system/tests/fixtures/design_gap/negative/missing_recommendation --strict
EXIT_CODE: 1
EXPECTED_FAILURE_STATUS: passed_expected_fail
BLOCKER: DG4_QUESTION_004 Recommended option is missing.

COMMAND: python3 agent-system/tools/aso/aso.py design verify --root agent-system/tests/fixtures/design_gap/negative/missing_rationale --strict
EXIT_CODE: 1
EXPECTED_FAILURE_STATUS: passed_expected_fail
BLOCKER: DG4_QUESTION_006 Recommendation reason is missing.

COMMAND: python3 agent-system/tools/aso/aso.py design verify --root agent-system/tests/fixtures/design_gap/negative/missing_blocking_stage --strict
EXIT_CODE: 1
EXPECTED_FAILURE_STATUS: passed_expected_fail
BLOCKERS: DG4_GAP_002, DG4_QUESTION_007, and DG4_SCHEMA_GAP_013.

COMMAND: python3 agent-system/tools/aso/aso.py design gate verify --root agent-system/tests/fixtures/design_gap/negative/unanswered_blocking_gap_crossing_stage --stage IMPLEMENTATION --strict
EXIT_CODE: 1
EXPECTED_FAILURE_STATUS: passed_expected_fail
BLOCKER: DG4_GATE_002 Stage gate blocked by unanswered gap.

COMMAND: python3 agent-system/tools/aso/aso.py design questions next --root agent-system/tests/fixtures/design_gap/negative/unaudited_question_presentation --json-out /tmp/aso-dg4-unaudited-question.json
EXIT_CODE: 1
EXPECTED_FAILURE_STATUS: passed_expected_fail
BLOCKER: DG4_AUDIT_001 Question is ready without audit pass evidence.
```

## Publication Boundary

```text
COMMAND: git status --short project-input project-runtime project-archive .venv
EXIT_CODE: 0
OUTPUT: ?? .venv/
INTERPRETATION: `.venv/` was created by required install validation and remained untracked before cleanup.

COMMAND: git ls-files project-input project-runtime project-archive .venv
EXIT_CODE: 0
OUTPUT: empty
OUTCOME: passed; no forbidden owner/runtime/archive/venv roots are tracked for publication.
```

No forbidden owner/runtime roots were published by this task. `project-input/`,
`project-runtime/`, `project-archive/`, and `.venv/` remain forbidden package
publication roots.

## Cleanup Evidence

Cleanup required by `FINAL_CLEANUP_AND_ACCEPTANCE.md` and
`CLEANUP_INSTRUCTIONS.md` was performed after accepted validation:

```bash
rm -rf project-input/aso_upgrade_project_design_gap_governance_p4_v3_6_0
rm -f project-input/aso_upgrade_project_design_gap_governance_p4_v3_6_0.zip
rm -rf .venv
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
git status --short
git ls-files project-input project-runtime project-archive .venv
```

```text
COMMAND: git status --short
EXIT_CODE: 0
OUTPUT:
 M agent-system/11_release/ASO_PROJECT_DESIGN_GAP_GOVERNANCE_P4_V3_6_0_RELEASE_NOTES.md
?? agent-system/11_release/ASO_PROJECT_DESIGN_GAP_GOVERNANCE_P4_V3_6_0_VALIDATION_REPORT.md

COMMAND: git ls-files project-input project-runtime project-archive .venv
EXIT_CODE: 0
OUTPUT: empty

COMMAND: find project-input -maxdepth 2 -print
EXIT_CODE: 0
OUTPUT: project-input
```

The cleanup removed only local DG4 package inputs, virtual environment files,
Python bytecode caches, and egg-info build metadata. It did not remove source
files under `agent-system/`, did not alter remote branches, and did not touch
the superseded product-intake P4 branch. Unrelated untracked historical
`project-runtime/` scratch material was not deleted because the DG4 cleanup
instructions did not authorize removing non-DG4 runtime material.

## Residual Risks

```text
FINAL_REPORT_COMMIT: not performed by profile agent.
STAGING_STATUS: no git add performed by profile agent.
PUSH_STATUS: no git push performed by profile agent.
REMOTE_CI_STATUS_AFTER_FINAL_PUSH: not claimed by profile agent; must be observed after orchestrator-owned commit/push.
```
