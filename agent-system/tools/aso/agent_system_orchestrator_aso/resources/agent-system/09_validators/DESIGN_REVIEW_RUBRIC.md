# DESIGN_REVIEW_RUBRIC

## Purpose

This document defines the deterministic audit rubric for `solution_architect`
design output.

The rubric is used by auditors after a solution architect or deprecated
`designer` alias returns a design RESULT. It converts the mandatory design
contract and traceability rules into explicit scoring and pass/fail criteria.

## Source documents

```text
agent-system/01_roles/SOLUTION_ARCHITECT.md
agent-system/03_templates/DESIGN_OUTPUT_CONTRACT.md
agent-system/07_lifecycle/DESIGN_STAGE.md
agent-system/09_validators/DESIGN_TRACEABILITY_RULES.md
agent-system/09_validators/RESULT_VALIDATION_RULES.md
agent-system/09_validators/TASK_PACKET_SCHEMA_VALIDATION_RULES.md
```

The required solution architect output contract is:

```text
agent-system/03_templates/DESIGN_OUTPUT_CONTRACT.md
```

Auditors must not pass design output that violates the output contract, even if
the numeric score below is otherwise high.

## Required audit evidence

Design audit evidence must include:

```text
DESIGN_OUTPUT_CONTRACT_STATUS: passed | failed | blocked | not_applicable
DESIGN_TRACEABILITY_STATUS: passed | failed | blocked | not_applicable
DESIGN_REVIEW_RUBRIC_SCORE: 0..100
DESIGN_REVIEW_RUBRIC_STATUS: passed | failed | blocked | not_applicable
DESIGN_REVIEW_FAIL_CONDITIONS:
```

`not_applicable` is allowed only when the audited RESULT is not a
`solution_architect` design output or deprecated `designer` alias output.

`blocked` is allowed only when the auditor cannot access the design RESULT,
required source documents, or changed design artifacts. Missing content inside
an accessible design output is `failed`, not `blocked`.

## Hard fail conditions

The auditor must check these conditions before assigning the numeric score.
When any condition is present, `DESIGN_REVIEW_RUBRIC_STATUS` is `failed`,
`DESIGN_REVIEW_RUBRIC_SCORE` is `0`, and auditor `STATUS: pass` is forbidden.

| ID | Required fail condition | Deterministic trigger |
| --- | --- | --- |
| DRF-001 | decision without source | Any accepted or proposed architecture decision lacks allowed `SOURCE_REFS` under `DESIGN_OUTPUT_CONTRACT.md`. |
| DRF-002 | assumption as fact / assumption presented as fact | Any assumption, GAP, research dependency, or unsupported claim is used as accepted requirement, architecture, runtime behavior, acceptance criteria, or task dependency. |
| DRF-003 | task without acceptance criteria | Any downstream dispatchable task packet or task proposal lacks acceptance criteria or has empty, `NONE`, or unrelated acceptance content. |
| DRF-004 | oversized task scope | Any task matches an oversized marker from `DESIGN_TRACEABILITY_RULES.md`: multiple responsible profile roles, mixed lifecycle ownership, repository-wide file authority, unrelated acceptance objectives, or stale-context dependency. |
| DRF-005 | missing test strategy | `TESTING_STRATEGY` is absent, non-substantive, or does not map implementation work and high-risk decisions to verification evidence. |
| DRF-006 | unresolved dependencies | A blocking dependency is unknown, informal, absent from `TASK_DAG`, or marked dispatchable without resolved source, upstream task, GAP, research dependency, or non-blocking rationale. |
| DRF-007 | missing owner decision marker | Owner input is required but no auditable `GAP_REGISTER_UPDATES` owner decision entry exists with question, options, recommendation, and blocking status. |
| DRF-008 | unclear product capability level | The design lacks an explicit product capability level, scope, acceptance reference, or source reference, or claims readiness beyond the supported gate. |
| DRF-009 | implementation task before required design gate | Any implementation-dependent task is dispatchable or `NEXT_ACTION`-eligible before design audit pass is represented in `TASK_DAG` or gate metadata. |

The required fail conditions are:

```text
decision without source
assumption as fact
assumption presented as fact
task without acceptance criteria
oversized task scope
missing test strategy
unresolved dependencies
missing owner decision marker
unclear product capability level
implementation task before required design gate
```

## Scoring model

Scoring is binary per row. Award the listed points only when the deterministic
check fully passes. Award `0` for that row when the check fails or evidence is
missing.

The maximum score is `100`.

| Area | Points | Deterministic pass condition |
| --- | ---: | --- |
| Output contract structure | 15 | Every required section from `DESIGN_OUTPUT_CONTRACT.md` is present or explicitly `NONE` with an auditable reason where the contract permits `NONE`. |
| Requirements traceability | 15 | Every in-scope requirement has `REQUIREMENT_ID`, `SOURCE_REF`, design response, downstream artifact mapping, acceptance link, and valid status. |
| Decision source quality | 15 | Every accepted or proposed architecture decision has allowed `SOURCE_REFS`, rationale, consequence, status, and task refs where implementation work exists. |
| Assumption/GAP/research separation | 10 | Assumptions, GAPs, and research dependencies are separated from accepted facts and decisions; blocking missing information is not hidden. |
| Downstream task readiness | 15 | Each task-like artifact is classified, schema status is recorded, acceptance criteria exist, scope is bounded, and `NEXT_ACTION` eligibility is compatible with validation status. |
| Dependency and gate readiness | 10 | `TASK_DAG`, dependencies, blockers, design audit gate, and checkpoint dependency are explicit and consistent. |
| Testing and audit plan | 10 | Testing strategy and audit plan cover MVP acceptance, high-risk decisions, downstream implementation checks, and required evidence. |
| Product capability and risk clarity | 10 | Product capability level, scope, acceptance reference, source reference, and risk ownership are explicit and do not overstate readiness. |

## Pass and fail rules

`DESIGN_REVIEW_RUBRIC_STATUS` is calculated after the hard fail check:

- `blocked` when required evidence is unavailable;
- `failed` when a hard fail condition exists or the score is below `90`;
- `passed` when no hard fail condition exists and the score is at least `90`;
- `not_applicable` only when the checked RESULT is not design output.

Auditor `STATUS: pass` is allowed only when all of these are true:

- `DESIGN_OUTPUT_CONTRACT_STATUS: passed`;
- `DESIGN_TRACEABILITY_STATUS: passed`;
- `DESIGN_REVIEW_RUBRIC_STATUS: passed`;
- `DESIGN_REVIEW_RUBRIC_SCORE` is at least `90`;
- `DESIGN_REVIEW_FAIL_CONDITIONS` is empty or contains only `NONE`;
- task packet schema evidence required by
  `TASK_PACKET_SCHEMA_VALIDATION_RULES.md` is `passed` or `not_applicable`;
- no required audit evidence status is failed, blocked, missing, unknown, or
  contradicted.

Auditor `STATUS: fail` is required when:

- any hard fail condition is present;
- the numeric score is below `90`;
- the design output contract is violated by accessible evidence;
- traceability status is `failed`;
- downstream task-like artifacts are invalid, ambiguous, unclassified, or
  selected for dispatch before validation and required gates.

Auditor `STATUS: blocked` is required when:

- the auditor cannot access a required RESULT, source document, changed design
  artifact, validator rule, or task-like artifact needed to score the rubric;
- the environment prevents required validation and no manual equivalent check
  can be performed.

Auditor `STATUS: gap` is allowed only when the audited RESULT itself correctly
identifies an owner-facing GAP and does not claim design pass for the blocked
surface. A missing owner decision marker is a fail condition, not a valid GAP.

## Required reporting format

Auditor evidence for this rubric must include:

```text
DESIGN_REVIEW_RUBRIC:
  DESIGN_OUTPUT_CONTRACT_STATUS:
  DESIGN_TRACEABILITY_STATUS:
  DESIGN_REVIEW_RUBRIC_SCORE:
  DESIGN_REVIEW_RUBRIC_STATUS:
  DESIGN_REVIEW_FAIL_CONDITIONS:
    - DRF-...
  SCORE_BREAKDOWN:
    OUTPUT_CONTRACT_STRUCTURE:
    REQUIREMENTS_TRACEABILITY:
    DECISION_SOURCE_QUALITY:
    ASSUMPTION_GAP_RESEARCH_SEPARATION:
    DOWNSTREAM_TASK_READINESS:
    DEPENDENCY_AND_GATE_READINESS:
    TESTING_AND_AUDIT_PLAN:
    PRODUCT_CAPABILITY_AND_RISK_CLARITY:
```

If no fail condition exists, the list must be:

```text
DESIGN_REVIEW_FAIL_CONDITIONS:
- NONE
```

## Non-overrides

This rubric does not override:

- profile-agent RESULT validation;
- task packet schema validation;
- filesystem governance;
- mandatory lifecycle transitions;
- profile-agent lifecycle termination validation;
- secret-safety rules;
- reasoning-level validation.

When any non-overridden validator forbids pass, design audit pass remains
forbidden even when this rubric scores at least `90`.
