# DESIGN_TRACEABILITY_RULES

## Purpose

This document defines deterministic traceability checks for
`solution_architect` design output.

Traceability validation exists to ensure that design decisions, downstream
tasks, dependencies, gates, and test strategy can be audited from explicit
sources instead of hidden context.

## Source documents

```text
agent-system/01_roles/SOLUTION_ARCHITECT.md
agent-system/03_templates/DESIGN_OUTPUT_CONTRACT.md
agent-system/07_lifecycle/DESIGN_STAGE.md
agent-system/09_validators/TASK_PACKET_SCHEMA_VALIDATION_RULES.md
agent-system/09_validators/RESULT_VALIDATION_RULES.md
```

The mandatory solution architect output structure is defined by:

```text
agent-system/03_templates/DESIGN_OUTPUT_CONTRACT.md
```

If this document conflicts with `DESIGN_OUTPUT_CONTRACT.md`, the contract wins
for output structure and this document must be corrected.

## Required status value

Design traceability evidence must use:

```text
DESIGN_TRACEABILITY_STATUS: passed | failed | blocked | not_applicable
```

`not_applicable` is allowed only when the checked RESULT is not a
`solution_architect` design output or deprecated `designer` alias output.

`blocked` is allowed only when a required design artifact, RESULT, or source
document is unavailable to the auditor. When the artifact is available but a
required marker or reference is missing, the status is `failed`.

## Required trace identifiers

The auditor must validate references using explicit identifiers from the design
output contract:

```text
REQUIREMENT_ID
SOURCE_REF
ACCEPTANCE_LINK
ASSUMPTION_ID
GAP_ID
DECISION_ID
MODULE_ID
DATA_CONTRACT_ID
TASK_OR_ARTIFACT_REF
RISK_ID
```

Validators must not infer a missing identifier from prose, file order, nearby
headings, or conversation context.

## Source traceability checks

Each in-scope requirement row in `REQUIREMENTS_TRACEABILITY_MATRIX` must contain
non-empty values for:

```text
REQUIREMENT_ID
SOURCE_REF
DESIGN_RESPONSE
DOWNSTREAM_ARTIFACTS
ACCEPTANCE_LINK
STATUS
```

Validation fails when:

- an in-scope requirement has no source reference;
- a downstream artifact has no traced requirement, accepted decision, GAP
  resolution, or required governance source;
- `STATUS: covered` is claimed without a design response and acceptance link;
- a deferred, gap, or out-of-scope item is not reflected in `NON_GOALS`,
  `GAP_REGISTER_UPDATES`, or a bounded future task proposal.

## Decision traceability checks

Every accepted or proposed item in `ARCHITECTURE_DECISIONS` must include:

```text
DECISION_ID
DECISION
SOURCE_REFS
RATIONALE
TASK_REFS
STATUS
```

Validation fails with `decision without source` when:

- an accepted or proposed decision has empty `SOURCE_REFS`;
- `SOURCE_REFS` contains only an assumption, GAP, research dependency, or
  informal memory reference;
- the source reference is not allowed by `DESIGN_OUTPUT_CONTRACT.md` source
  rules.

Assumptions may appear in `ASSUMPTION_REFS`, but they must not replace
`SOURCE_REFS`.

## Assumption and fact separation checks

Every factual claim that drives scope, architecture, runtime behavior, module
contracts, data contracts, testing, or task decomposition must be one of:

```text
SOURCE_BACKED
ASSUMPTION
GAP
RESEARCH_DEPENDENCY
```

Validation fails with `assumption as fact` or `assumption presented as fact`
when:

- a non-source-backed claim is used as accepted scope, accepted architecture,
  accepted runtime behavior, or accepted task acceptance criteria;
- an item listed in `ASSUMPTIONS_REGISTER` is also used as the sole basis for
  an accepted architecture decision;
- an assumption that blocks design acceptance is not promoted to
  `GAP_REGISTER_UPDATES` or bounded research dependency work.

## Owner decision checks

Owner decisions and owner-provided missing information must be represented in
`GAP_REGISTER_UPDATES`.

The GAP entry must include:

```text
GAP_ID
TYPE
STATUS
BLOCKS
QUESTION_TO_OWNER
RECOMMENDED_OPTIONS
RECOMMENDED_OPTION
REASON
TARGET_REGISTER
```

Validation fails with `missing owner decision marker` when:

- the design says owner input, product choice, business rule approval, scope
  approval, or acceptance approval is required but no GAP entry exists;
- the GAP entry omits the owner-facing question or recommended options;
- a downstream task depends on an owner decision but the dependency is not
  marked blocked or gap.

## Downstream task traceability checks

Every downstream task-like artifact in `DISPATCHABLE_TASK_PACKETS` must trace
to at least one of:

```text
REQUIREMENT_ID
DECISION_ID
GAP_ID resolved by accepted owner input
RISK_ID requiring mitigation
governance requirement from an allowed source
```

Validation fails with `task without acceptance criteria` when:

- a dispatchable task packet or task proposal lacks acceptance criteria;
- `ACCEPTANCE_SUMMARY` is empty, `NONE`, or unrelated to the traced source;
- a task packet cannot be validated against
  `TASK_PACKET_SCHEMA_VALIDATION_RULES.md` because acceptance criteria are
  missing.

Validation fails with `oversized task scope` when any downstream task-like
artifact has one or more of these deterministic markers:

- more than one profile execution role is responsible for delivery in the same
  task;
- implementation, independent testing, technical writing, setup, launch, or
  release work are combined in one task without separate gated task packets;
- `ALLOWED_FILE_CHANGES` is repository-wide, such as `.`, `*`, `**/*`, or the
  repository root, without narrower path limits;
- acceptance criteria require unrelated feature delivery, architecture redesign,
  test ownership, and documentation ownership in the same task;
- the task cannot be completed by a fresh profile-agent context using only its
  listed required docs, inputs, acceptance criteria, and bounded file authority.

## Dependency and gate traceability checks

Every dependency listed in `TASK_DAG`, `DISPATCHABLE_TASK_PACKETS`, module
contracts, data contracts, testing strategy, or runtime model must have one of:

```text
resolved source reference
upstream task or artifact reference
GAP_ID
RESEARCH_DEPENDENCY_REF
explicit non-blocking rationale
```

Validation fails with `unresolved dependencies` when:

- `DEPENDENCIES` or `DEPENDS_ON` contains unknown, empty, `TBD`, or informal
  dependency text;
- a dependency blocks downstream execution but the task is marked dispatchable;
- a dependency is required for acceptance but is absent from `TASK_DAG`;
- a cross-module or data dependency is not represented in task order.

Validation fails with `implementation task before required design gate` when:

- an implementation, setup, launch, testing, documentation, or release task is
  dispatchable before design audit pass is represented in `TASK_DAG`;
- `NEXT_ACTION_ELIGIBLE: yes` is claimed for implementation work before the
  required design audit and checkpoint gates;
- `GATE_REQUIRED` is empty, `NONE`, or omits the required design audit gate for
  downstream implementation work.

Accepted gate markers for implementation-dependent work are:

```text
design_audit_pass
design_audit_pass_then_checkpoint
accepted_design_artifact
```

Equivalent prose is valid only when it names the design audit pass explicitly.

## Test strategy traceability checks

`TESTING_STRATEGY` must map MVP acceptance, high-risk architecture decisions,
and implementation tasks to concrete verification evidence.

Validation fails with `missing test strategy` when:

- `TESTING_STRATEGY` is absent;
- every testing strategy field is empty, `NONE`, or not applicable without an
  auditable reason;
- implementation tasks do not identify expected checks or whether separate
  tester work is required;
- high-risk decisions have no verification path.

## Product capability checks

Every design output must state the current product capability claim for the
designed scope. The claim may appear in `MVP_BOUNDARY`, `RUNTIME_MODEL`,
`AUDIT_PLAN`, or an explicit `PRODUCT_CAPABILITY_LEVEL` field.

The claim must include:

```text
PRODUCT_CAPABILITY_LEVEL:
CAPABILITY_SCOPE:
CAPABILITY_ACCEPTANCE_REF:
CAPABILITY_SOURCE_REF:
```

Allowed capability levels for traceability validation are:

```text
skeleton
task_complete
product_slice
mvp_candidate
launch_candidate
final_acceptance_candidate
not_applicable
```

`not_applicable` must include an auditable reason.

Validation fails with `unclear product capability level` when:

- no capability claim is present;
- the design claims generic completion, readiness, MVP, launch readiness, or
  final acceptance without one allowed level;
- the capability level lacks scope, acceptance, or source reference;
- a skeleton or task-level result is described as product, MVP, launch, or
  final acceptance ready without a supporting accepted gate.

When a design output claims or prepares `capability_pass`, `product_pass`,
`mvp_ready`, or `final_acceptance`, it must also follow the capability matrix
and gate vocabulary in `PRODUCT_CAPABILITY_GATE_POLICY.md`.

## Pass criteria

`DESIGN_TRACEABILITY_STATUS: passed` is allowed only when:

- every required contract section needed for traceability is present;
- source-backed decisions, assumptions, GAPs, and research dependencies are not
  mixed;
- every downstream task-like artifact has source trace, acceptance criteria,
  bounded scope, dependencies, and gate status;
- testing strategy and product capability level are explicit;
- no fail condition from this document is present.

Any fail condition in this document forbids auditor `STATUS: pass`.
