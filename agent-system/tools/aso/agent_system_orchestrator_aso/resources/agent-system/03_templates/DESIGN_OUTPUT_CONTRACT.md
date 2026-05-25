# DESIGN_OUTPUT_CONTRACT

## Purpose

This contract defines the mandatory structure for `solution_architect` design
outputs.

It applies to solution architect RESULT evidence, bounded design artifacts,
and downstream task decomposition produced by the design stage. It is not a
dispatchable task packet and must not be used as `NEXT_ACTION.TASK_PACKET`.

Design output is valid only when it:

- traces requirements to design decisions and downstream tasks;
- separates accepted facts, assumptions, GAPs, and research dependencies;
- records each architecture decision with an explicit source;
- creates downstream work that can be audited and converted into dispatchable
  task packets without relying on hidden context.

## Source Rules

The solution architect may cite only source-of-truth inputs allowed by:

```text
agent-system/01_roles/SOLUTION_ARCHITECT.md
agent-system/07_lifecycle/DESIGN_STAGE.md
```

Every factual claim that drives scope, architecture, runtime behavior, module
contracts, data contracts, testing, or task decomposition must be one of:

```text
SOURCE_BACKED:
  backed by an allowed source reference

ASSUMPTION:
  explicitly listed in ASSUMPTIONS_REGISTER and not treated as accepted fact

GAP:
  explicitly listed in GAP_REGISTER_UPDATES when owner decision or
  owner-provided information is required

RESEARCH_DEPENDENCY:
  explicitly represented as bounded research work when a missing fact can be
  researched from allowed sources
```

Assumptions, GAPs, and research dependencies must not be mixed into
architecture decisions as if they were accepted facts.

## Required Sections

Every solution architect design output must include the following sections.
Sections may say `NONE` only when the design task genuinely has no applicable
content for that section and the reason is auditable.

## REQUIREMENTS_TRACEABILITY_MATRIX

Map each accepted requirement, source brief item, GAP resolution, or accepted
research input to design output.

Required fields per row:

```text
REQUIREMENT_ID:
SOURCE_REF:
DESIGN_RESPONSE:
DOWNSTREAM_ARTIFACTS:
ACCEPTANCE_LINK:
STATUS: covered | deferred | gap | out_of_scope
```

Rules:

- every in-scope requirement must map to at least one design response or
  downstream task;
- deferred or uncovered requirements must appear in `GAP_REGISTER_UPDATES`,
  `NON_GOALS`, or bounded future task proposals;
- no downstream task may exist without a traced requirement, accepted
  architecture decision, GAP resolution, or required governance activity.

## MVP_BOUNDARY

Define the minimum accepted scope for the current design pass.

Required content:

```text
IN_SCOPE:
OUT_OF_SCOPE:
MVP_ACCEPTANCE:
DEFERRALS:
SOURCE_REFS:
```

Rules:

- MVP scope must be small enough for bounded downstream task packets;
- MVP acceptance must be testable;
- deferred scope must not be hidden inside implementation task acceptance
  criteria.

## NON_GOALS

List explicit exclusions for this design pass.

Required fields per item:

```text
NON_GOAL_ID:
DESCRIPTION:
REASON:
SOURCE_OR_DECISION_REF:
IMPACT_ON_TASKS:
```

Rules:

- non-goals prevent downstream task scope expansion;
- excluded features must not appear in `DISPATCHABLE_TASK_PACKETS`.

## ASSUMPTIONS_REGISTER

List assumptions that are useful for planning but not accepted as facts.

Required fields per item:

```text
ASSUMPTION_ID:
STATEMENT:
BASIS:
IMPACT:
VALIDATION_PATH: owner_decision | research_dependency | implementation_check | audit_check | none
EXPIRY_OR_REVIEW_TRIGGER:
```

Rules:

- assumptions must not be used as the sole source for architecture decisions;
- assumptions that block design acceptance must become GAPs or research
  dependencies;
- task packets may reference assumptions only as risks or validation notes, not
  as accepted requirements.

## GAP_REGISTER_UPDATES

List GAPs that must be created, updated, resolved, or left open.

Required fields per item:

```text
GAP_ID:
TYPE:
STATUS: new | update | resolved | open
BLOCKS:
QUESTION_TO_OWNER:
RECOMMENDED_OPTIONS:
RECOMMENDED_OPTION:
REASON:
TARGET_REGISTER:
```

Rules:

- owner decisions and missing owner-provided information must be GAPs, not
  research dependencies;
- unresolved blocking GAPs prevent `STATUS: pass`;
- non-blocking GAPs must state why downstream task packets remain safe.

## ARCHITECTURE_DECISIONS

Record architecture decisions required for implementation, testing, runtime,
or task decomposition.

Required fields per decision:

```text
DECISION_ID:
DECISION:
SOURCE_REFS:
OPTIONS_CONSIDERED:
RATIONALE:
CONSEQUENCES:
ASSUMPTION_REFS:
GAP_REFS:
RESEARCH_DEPENDENCY_REFS:
TASK_REFS:
STATUS: accepted | proposed | blocked | deferred
```

Rules:

- every accepted or proposed decision must include at least one `SOURCE_REFS`
  entry from an allowed source;
- assumptions may inform risk but must not replace `SOURCE_REFS`;
- decisions blocked by missing owner input must reference `GAP_REFS`;
- decisions blocked by missing researchable facts must reference
  `RESEARCH_DEPENDENCY_REFS`.

## MODULE_CONTRACTS

Define module, service, package, UI, CLI, workflow, or integration boundaries
that downstream agents must respect.

Required fields per module:

```text
MODULE_ID:
PURPOSE:
OWNED_BEHAVIOR:
PUBLIC_INTERFACE:
DEPENDENCIES:
INPUTS:
OUTPUTS:
ERROR_HANDLING:
FILES_OR_PATHS:
TASK_REFS:
SOURCE_REFS:
```

Rules:

- module contracts must be concrete enough for bounded implementation tasks;
- each module with implementation work must map to at least one task packet or
  proposal;
- cross-module dependencies must appear in `TASK_DAG`.

## DATA_CONTRACTS

Define persistent data, in-memory data, file formats, schemas, API payloads,
configuration, and state transitions relevant to the design.

Required fields per contract:

```text
DATA_CONTRACT_ID:
ENTITY_OR_PAYLOAD:
FIELDS:
VALIDATION_RULES:
LIFECYCLE_OR_STATE_RULES:
READERS:
WRITERS:
BACKWARD_COMPATIBILITY:
SECURITY_OR_PRIVACY_NOTES:
SOURCE_REFS:
TASK_REFS:
```

Rules:

- data contracts must identify owners of reads and writes;
- stateful contracts must include lifecycle rules or state transitions;
- secrets must be referenced by path, variable name, or class only, never by
  value.

## RUNTIME_MODEL

Describe how the designed system runs, starts, stops, observes health, and
handles failure within the current scope.

Required content:

```text
ENTRYPOINTS:
PROCESS_MODEL:
CONFIGURATION:
STATE_AND_STORAGE:
EXTERNAL_DEPENDENCIES:
FAILURE_MODES:
OBSERVABILITY:
LOCAL_RUN_OR_SMOKE_COMMANDS:
SOURCE_REFS:
TASK_REFS:
```

Rules:

- runtime claims require source references or must be assumptions, GAPs, or
  research dependencies;
- runtime requirements that need setup, launch, run, or handover work must map
  to downstream tasks.

## TESTING_STRATEGY

Define verification responsibility for the design and downstream work.

Required content:

```text
UNIT_OR_STATIC_CHECKS:
INTEGRATION_CHECKS:
RUNTIME_SMOKE_CHECKS:
ACCEPTANCE_SCENARIOS:
NEGATIVE_OR_FAILURE_CHECKS:
EVIDENCE_REQUIRED:
TESTING_TASK_REFS:
SOURCE_REFS:
```

Rules:

- testing strategy must cover MVP acceptance and high-risk architecture
  decisions;
- each implementation task must state its own expected checks and whether a
  separate tester task is required;
- missing tooling must be listed as a risk, GAP, or setup task.

## TASK_DAG

Define execution order, dependencies, gates, and continuation paths.

Required fields per node:

```text
NODE_ID:
TASK_OR_ARTIFACT_REF:
ROLE:
DEPENDS_ON:
UNBLOCKS:
GATE_REQUIRED:
DISPATCH_STATUS: dispatchable | non_dispatchable | blocked | gap
```

Rules:

- implementation work must not precede required design audit pass;
- research dependency continuation must follow `DESIGN_RESEARCH_LOOP.md`;
- task order must allow fresh profile-agent contexts to work without stale
  conversation context.

## DISPATCHABLE_TASK_PACKETS

List every downstream task-like artifact created or required by the design.

Required fields per artifact:

```text
ARTIFACT_REF:
CLASSIFICATION: task_packet | task_proposal | research_dependency | design_continuation
DISPATCH_STATUS: dispatchable | non_dispatchable | blocked | gap
SCHEMA_STATUS: not_checked | passed | failed | blocked | not_applicable
TARGET_ROLE:
TASK_KIND:
REQUIRED_DOCS:
ACCEPTANCE_SUMMARY:
DEPENDENCIES:
NEXT_ACTION_ELIGIBLE: yes | no
```

Rules:

- a dispatchable task packet must declare `# TASK PACKET`, conform to
  `agent-system/03_templates/TASK_PACKET_TEMPLATE.md`, and pass
  `agent-system/09_validators/TASK_PACKET_SCHEMA_VALIDATION_RULES.md`;
- a non-dispatchable proposal must declare `# TASK PROPOSAL` or
  `TASK_PROPOSAL`, conform to
  `agent-system/03_templates/TASK_PROPOSAL_TEMPLATE.md`, and contain
  `DISPATCH_STATUS: non_dispatchable`;
- `NEXT_ACTION_ELIGIBLE: yes` is allowed only for schema-passed dispatchable
  task packets after required design audit and checkpoint gates;
- task packets must be usable by downstream agents from their own
  `REQUIRED_DOCS`, `INPUTS`, acceptance criteria, audit requirements, and
  bounded file authority.

## AUDIT_PLAN

Define what the auditor must verify for design acceptance and downstream
packet readiness.

Required content:

```text
DESIGN_SCOPE_CHECKS:
SOURCE_TRACEABILITY_CHECKS:
ASSUMPTION_GAP_RESEARCH_SEPARATION_CHECKS:
DECISION_SOURCE_CHECKS:
TASK_PACKET_SCHEMA_CHECKS:
DOWNSTREAM_DISPATCH_CHECKS:
RISK_CHECKS:
REQUIRED_EVIDENCE:
```

Rules:

- audit must verify that decisions have sources;
- audit must verify that assumptions, GAPs, and research dependencies are
  separated;
- audit must verify downstream task-like artifacts are classified and validated
  before any dispatch or checkpoint reliance.

## RISK_REGISTER

List design, implementation, runtime, governance, testing, security, and
delivery risks.

Required fields per risk:

```text
RISK_ID:
CATEGORY:
DESCRIPTION:
LIKELIHOOD:
IMPACT:
MITIGATION:
OWNER_OR_NEXT_TASK:
SOURCE_OR_DECISION_REF:
STATUS: open | mitigated | accepted | transferred
```

Rules:

- risks tied to assumptions must reference `ASSUMPTION_ID`;
- risks tied to unresolved owner input must reference `GAP_ID`;
- risks that require implementation, testing, setup, audit, or documentation
  work must map to a task or proposal.

## Pass Criteria

A solution architect design output may return `STATUS: pass` only when:

- every required section is present;
- every accepted architecture decision has an allowed source reference;
- assumptions, GAPs, and research dependencies are separated;
- unresolved blockers are absent or the RESULT returns `STATUS: gap` or
  `STATUS: blocked`;
- downstream task packets or proposals are classified;
- dispatchable task packets are schema-valid or explicitly marked as not yet
  eligible for `NEXT_ACTION`;
- downstream agents can execute task packets using only listed source docs,
  inputs, acceptance criteria, and bounded file authority.
