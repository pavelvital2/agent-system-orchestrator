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

## Template link checks

Every template referenced by role, runtime, state, validator, smoke, or README
docs must exist in `agent-system/03_templates/`, `agent-system/04_state/`,
`agent-system/05_gap_flow/`, or `agent-system/06_logs/` as applicable.

Template validation must catch stale template names, missing schema sidecars
when a sidecar is documented as present, and references that use a non-canonical
template path for the same package object.

Task packet validation must compare `TASK_PACKET_TEMPLATE.md` with
`schemas/task_packet.schema.json`. Their required fields must remain in parity
for task identity, lifecycle, role routing, scope boundaries, source-of-truth
documents, dependencies, acceptance criteria, evidence requirements, audit
requirements, next-role routing, and result format. A field required by one and
omitted by the other is a cross-link validation failure unless the difference is
explicitly documented as a compatibility alias.

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
