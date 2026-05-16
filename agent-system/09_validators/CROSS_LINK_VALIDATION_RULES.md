# CROSS_LINK_VALIDATION_RULES

## Purpose

This document defines documentation-first checks for package-internal
cross-links and file dependencies.

Cross-link validation confirms that package docs refer to existing package
files, use canonical runtime names, and keep role, lifecycle, template,
validator, runtime, and README references aligned. It does not require a CLI,
script, service, repository remote, deployment, or credential access.

## Source documents

```text
agent-system/README.md
agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
agent-system/09_validators/VALIDATOR_SPEC.md
agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
```

Cross-link rules complement the validator set documented in
[VALIDATOR_SPEC.md](VALIDATOR_SPEC.md).

## Required path checks

Every path referenced as a required package file must exist in the package.

Validators and final smoke review must check at least:

- package files listed in `FINAL_SMOKE_CHECKLIST.md`;
- validator documents listed in `VALIDATOR_SPEC.md`;
- lifecycle stage files listed in `PROJECT_LIFECYCLE.md`;
- package entry, versioning, governance, example, template, state, log, profile,
  runtime, role, and validator files referenced from `README.md`.

Missing required package files are invalid unless the referencing document
explicitly marks the path as an optional future extension.

## README link checks

Every start, runtime, template, state, log, profile, lifecycle, validator,
example, versioning, and governance document referenced in `README.md` must
exist.

README validation must also confirm that the README links to this document:

```text
agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
```

## Lifecycle link checks

Every lifecycle stage listed in `PROJECT_LIFECYCLE.md` must have one of:

- an existing stage document;
- an explicit alias that states why no separate stage document exists.

Lifecycle validation must cover the documented lifecycle order and the stage
document list. A stage reference is invalid when the order mentions a stage but
neither the stage document list nor an explicit alias accounts for it.

Lifecycle validation must confirm that `PROJECT_LIFECYCLE.md` explicitly aliases
`AUDIT` without `AUDIT_STAGE.md` and `FINAL_ACCEPTANCE` without
`FINAL_ACCEPTANCE_STAGE.md`. These aliases must not create new standalone stage
documents or new profile-role authority.

Bootstrap lifecycle validation must also cross-check:

```text
agent-system/00_start/ORCHESTRATOR_START.md
agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
agent-system/07_lifecycle/REQUIREMENTS_STAGE.md
agent-system/07_lifecycle/DESIGN_STAGE.md
```

The bootstrap, lifecycle, requirements, and design documents are inconsistent
if they make designer the only valid first profile agent, omit the
requirements_analyst route for incomplete, ambiguous, or uncertain owner input,
or allow direct designer routing without sufficiently structured owner input.

Bootstrap task packet path validation must cross-check
`FILESYSTEM_GOVERNANCE.md`, `STATE_TRANSITION_RULES.md`,
`ORCHESTRATOR_RUNTIME_LOOP.md`, `TASK_PACKET_VALIDATION_RULES.md`,
`FINAL_SMOKE_CHECKLIST.md`, and `EXPECTED_FLOW_EXAMPLE.md`. These documents are
inconsistent if they allow any active task packet outside `ACTIVE_DOC_ROOT`
other than the single governed first bootstrap packet:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

They are also inconsistent if they treat ordinary task packets outside
`ACTIVE_DOC_ROOT` as valid, treat a handoff file as a task packet substitute,
allow profile-agent dispatch without a task packet, or allow more than one
active first bootstrap task packet at the same time.

## Role link checks

Every role referenced in templates, state files, transition rules, validator
rules, or README routing text must map to one of:

- an existing role file in `agent-system/01_roles/`;
- an explicit control or routing pseudo-role defined by validator rules.

Profile execution roles must have matching role files. Control and routing
pseudo-roles must not be treated as dispatchable profile execution roles.

When `STATE_TRANSITION_RULES.md` or validator rules define a mandatory
profile-agent audit transition, the documented profile execution role set must
resolve to existing role files and must include:

```text
requirements_analyst
designer
developer
tester
technical_writer
devops_setup_engineer
release_manager
```

Cross-link validation must flag a profile role as inconsistent if its
mandatory-audit pass routing is absent, points directly to another profile
role, points directly to another lifecycle phase, points directly to terminal
completion, or points directly to a Git checkpoint before auditor `STATUS:
pass`.

Profile-role transition validation must cross-check
`STATE_TRANSITION_RULES.md` against every role enum or profile-role set in
runtime state, task packet, result, gate, validator, and README docs. The
covered v1.2.0 profile execution role set is:

```text
requirements_analyst
designer
developer
auditor
tester
technical_writer
devops_setup_engineer
release_manager
```

For mandatory-audit pass routing, all non-auditor profile execution roles in
that set must route to auditor before accepted state, next phase, terminal
completion, or Git checkpoint.

## Template link checks

Every template referenced by role, runtime, state, validator, smoke, or README
docs must exist in `agent-system/03_templates/`, `agent-system/04_state/`,
`agent-system/05_gap_flow/`, or `agent-system/06_logs/` as applicable.

Template validation must catch stale template names, missing schema sidecars
when a sidecar is documented as present, and references that use a non-canonical
template path for the same package object.

Schema sidecar validation must catch stale sidecar lists across validator,
runtime state schema, and final smoke source-of-truth documents. A sidecar that
exists and is listed as a package validation target in one source-of-truth list
must not be omitted from another source-of-truth list that enumerates package
schema sidecars.

Task packet validation must compare `TASK_PACKET_TEMPLATE.md` with
`schemas/task_packet.schema.json`. Their required fields must remain in parity
for task identity, lifecycle, role routing, scope boundaries, source-of-truth
documents, dependencies, acceptance criteria, evidence requirements, audit
requirements, next-role routing, and result format. A field required by one and
omitted by the other is a cross-link validation failure unless the difference is
explicitly documented as a compatibility alias.

Minimal fixture validation must cross-check:

```text
agent-system/10_examples/MINIMAL_EXAMPLE_FIXTURE.md
agent-system/10_examples/EXPECTED_FLOW_EXAMPLE.md
agent-system/04_state/RUNTIME_STATE_SCHEMA.md
agent-system/03_templates/TASK_PACKET_TEMPLATE.md
agent-system/09_validators/schemas/task_packet.schema.json
```

The fixture is inconsistent if its runtime seed omits active version tuple
fields, uses stale `NEXT_ACTION` field names, omits canonical runtime file
dependencies, or shows a task packet shape that conflicts with the current task
packet template or schema. Example task packets must use
`MANDATORY_WORKFLOW`, `NEXT_ROLE_ON_PASS`, `NEXT_ROLE_ON_FAIL`,
`NEXT_ROLE_ON_BLOCKED`, and `NEXT_ROLE_ON_GAP` for outcome routing, and must
not include RESULT-only fields such as `NEXT_RECOMMENDED_ACTION`.

PROJECT_STATE semantic field validation must compare
`PROJECT_STATE_TEMPLATE.md`, `RUNTIME_STATE_SCHEMA.md`, and
`schemas/project_state.schema.json`. `ACTION_SEMANTIC` and `SEMANTIC_REASON`
must have the same mandatory status in all three sources, and any example that
directly enumerates `PROJECT_STATE` fields must include them or explicitly
delegate to the template.

## Validator link checks

Every validator document referenced by `VALIDATOR_SPEC.md`, README, or the
final smoke checklist must exist.

The required validator document set includes:

```text
agent-system/09_validators/RUNTIME_CONSISTENCY_RULES.md
agent-system/09_validators/RESULT_VALIDATION_RULES.md
agent-system/09_validators/TASK_PACKET_VALIDATION_RULES.md
agent-system/09_validators/TRANSITION_VALIDATION_RULES.md
agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md
agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
```

If a validator is referenced by smoke evidence or another validator rule, the
path must resolve to an existing package file.

## Runtime file name checks

Required runtime file references must use one canonical name for each runtime
file across start, runtime, template, state, validator, and smoke docs.

The canonical required runtime file set is:

```text
project-runtime/PROJECT_STATE.md
project-runtime/CURRENT_GATE.md
project-runtime/NEXT_ACTION.md
project-runtime/GAP_REGISTER.md
project-runtime/AGENT_RESULTS_LOG.md
project-runtime/TASK_REGISTRY.md
project-runtime/ACCEPTED_ARTIFACTS.md
project-runtime/ORCHESTRATOR_EVENTS_LOG.md
project-runtime/STATUS_SUMMARY.md
```

Cross-link validation checks name consistency for these runtime dependencies.
It must not require the runtime directory to exist during package-only smoke
review unless the active task explicitly includes runtime initialization.

Cross-link validation must also detect stale authoritative runtime source-of-
truth lists. A current package document is stale when it presents only this
legacy five-file set as complete:

```text
project-runtime/PROJECT_STATE.md
project-runtime/CURRENT_GATE.md
project-runtime/NEXT_ACTION.md
project-runtime/GAP_REGISTER.md
project-runtime/AGENT_RESULTS_LOG.md
```

Any such list must be corrected to the canonical nine-file runtime set above or
must be explicitly marked as a partial example. Current start, runtime loop,
orchestrator role, runtime schema, filesystem governance, validator, and final
smoke documents must not use the legacy five-file set as the complete runtime
source of truth.

## Git authority cross-link checks

Git authority validation must cross-check:

```text
agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
agent-system/01_roles/REQUIREMENTS_ANALYST.md
agent-system/01_roles/DESIGNER.md
agent-system/01_roles/DEVELOPER.md
agent-system/01_roles/AUDITOR.md
agent-system/01_roles/TESTER.md
agent-system/01_roles/TECHNICAL_WRITER.md
agent-system/01_roles/DEVOPS_SETUP_ENGINEER.md
agent-system/01_roles/RELEASE_MANAGER.md
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
```

These documents are inconsistent if they allow a profile agent, auditor, or
task packet to bypass the orchestrator-owned post-audit Git checkpoint, commit
or push without auditor `STATUS: pass`, or stage files outside the audited task
allowed scope.

## Final pre-1.2.1 readiness checks

Final pre-1.2.1 readiness validation must cross-check the final smoke checklist
against the bootstrap, task packet, runtime, validator, example, README,
versioning, and changelog documents. It is a documentation-level package smoke
check and must not install a new package version or require runtime
initialization.

The readiness check fails if any current package document contradicts the
canonical bootstrap task packet path:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

The readiness check also fails if the bootstrap exception is not propagated
consistently as the only active task packet exception outside
`ACTIVE_DOC_ROOT`, if ordinary task packets outside `ACTIVE_DOC_ROOT` are
treated as valid, if handoff files are treated as task packets, if first
profile-agent dispatch can use `TASK_PACKET: NONE`, or if examples allow
profile agents to write runtime-owned state paths.

Task packet example/schema parity must be verified by comparing examples with
`TASK_PACKET_TEMPLATE.md` and `schemas/task_packet.schema.json`. Example task
packets must use task-packet routing fields such as `MANDATORY_WORKFLOW` and
`NEXT_ROLE_ON_*`; they must not use RESULT-only routing fields such as
`NEXT_RECOMMENDED_ACTION`.

Bootstrap task packet parity must also compare
`BOOTSTRAP_TASK_PACKET_TEMPLATE.md` with `schemas/task_packet.schema.json`.
The bootstrap template must not include standalone non-schema task-packet fields
such as `REQUESTER`, must not include standalone RESULT-only fields such as
`NEXT_RECOMMENDED_ACTION`, must use the canonical placeholder
`project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md`, and must map
bootstrap role documents explicitly to
`agent-system/01_roles/REQUIREMENTS_ANALYST.md` and
`agent-system/01_roles/DESIGNER.md`.

Runtime schema parity must compare `RUNTIME_STATE_SCHEMA.md`,
`CURRENT_GATE_TEMPLATE.md`, `NEXT_ACTION_TEMPLATE.md`,
`schemas/current_gate.schema.json`, and `schemas/next_action.schema.json`.
`CURRENT_GATE` and `NEXT_ACTION` mandatory fields must be represented directly
or by documented Markdown section-to-schema mapping.

Changelog traceability must verify that accepted governance changelog entries
cover the current correction-chain scope, representative affected files,
affected invariants, unchanged active version tuple, absence of v1.2.1
installation, and absence of reasoning-level policy changes.

## Changelog traceability checks

Governance changelog validation must cross-check
`agent-system/GOVERNANCE_CHANGELOG.md` against files changed by each accepted
v1.2.0 correction task in the correction chain. Changelog traceability is
incomplete if the changelog omits the changed files, affected invariants,
version tuple impact, migration impact, audit requirement, or status needed to
replay why a final smoke or cross-link correction was accepted.

## Project-agnostic check

Package core docs must not reference project-specific entities, business-domain
terms, credentials, external account names, or implementation-specific platform
assumptions.

If a path or term appears to belong to a project rather than the universal
package, the validator must classify it as invalid unless it is clearly inside
an example fixture and remains generic.

## Failure handling

Any missing required file, stale reference, stale runtime source-of-truth list,
non-canonical runtime name, unresolved lifecycle stage, unresolved profile
execution role, unresolved template, task packet template/schema parity
mismatch, unresolved validator, or project-specific core reference is a
cross-link validation failure.

The orchestrator must route failures through governed correction flow. Profile
agents must not bypass audit, mark the package accepted, or perform Git
checkpoint actions from a cross-link validation result alone.
