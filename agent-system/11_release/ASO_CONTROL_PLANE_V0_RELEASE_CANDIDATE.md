# ASO_CONTROL_PLANE_V0_RELEASE_CANDIDATE

## Purpose

This document records stable release evidence for the ASO control-plane v0
release candidate before cleanup of the root `project-runtime/` directory.

The report summarizes accepted package state and durable documentation. It does
not copy raw runtime dumps and does not require `project-runtime/` to exist
after cleanup.

## Evidence Basis

Durable package evidence is maintained in these files:

```text
agent-system/README.md
agent-system/PACKAGE_VERSIONING.md
agent-system/GOVERNANCE_CHANGELOG.md
agent-system/tools/aso/aso.py
agent-system/tools/aso/commands/status.py
agent-system/tools/aso/commands/lint.py
agent-system/tools/aso/commands/archive_verify.py
agent-system/01_roles/SOLUTION_ARCHITECT.md
agent-system/02_runtime/PROFILE_AGENT_LIFECYCLE.md
agent-system/02_runtime/RUNTIME_FILE_TAXONOMY.md
agent-system/02_runtime/TRANSACTIONAL_CHECKPOINT_SPEC.md
agent-system/02_runtime/CANONICAL_JSON_STATE_PREPARATION.md
agent-system/09_validators/REASONING_LEVEL_VALIDATION_RULES.md
agent-system/09_validators/PRODUCT_CAPABILITY_GATE_POLICY.md
agent-system/scripts/run_governance_smoke_tests.sh
agent-system/scripts/run_governance_smoke_tests.py
```

Pre-cleanup runtime summaries were used only as transient corroboration while
creating this document. The stable release evidence is the package content
summarized below.

## Release Candidate Summary

### ASO v0 scope: read-only helper CLI status/lint/archive verify

ASO v0 provides a read-only helper CLI for control-plane inspection. The CLI
entry point is `agent-system/tools/aso/aso.py` and currently exposes:

- `aso status`, which reads runtime Markdown files and summarizes project,
  branch, gate, checkpoint, next-action, push, and consistency state;
- `aso lint`, which reports runtime consistency findings without mutating
  project files;
- `aso archive verify`, which inspects supported archive formats for required
  ASO project content and accepted artifact evidence.

The v0 boundary is intentionally diagnostic. The CLI does not dispatch agents,
commit, push, checkpoint, migrate runtime state, or repair files.

### reasoning level policy: low/medium/high/xhigh

The reasoning level policy now uses only these canonical values:

```text
low
medium
high
xhigh
```

Deprecated values such as `default`, `maximum`, and `role_default` are not
valid `REASONING_LEVEL.VALUE` strings in new task packets. Role defaults and
gate floors resolve to one of the four canonical values before dispatch.
Validation orders them as:

```text
low < medium < high < xhigh
```

Tasks may raise reasoning level freely. Lowering below role default or gate
floor is restricted to mechanical bounded work and requires explicit override
evidence.

### solution_architect role and designer alias

The canonical design role is `solution_architect`. It owns requirements
interpretation, architecture, bounded scope, contracts, task decomposition, and
design traceability. The older `designer` role name remains only as a
deprecated compatibility alias mapped to `solution_architect`.

Design output is governed by the solution architect role file, design output
contract, traceability rules, and review rubric. The role does not implement
production code, audit its own design, replace release/testing/documentation
roles, commit, or push.

### one-agent-one-task-one-result lifecycle

The profile-agent lifecycle policy is:

```text
one agent = one task = one RESULT
```

Profile-agent reuse is forbidden. Each fresh profile-agent instance receives
one bounded task packet, returns one structured `RESULT`, and must then be
logically terminated. Required lifecycle fields include `TASK_ID`,
`AGENT_INSTANCE_ID`, `REUSE_ALLOWED: false`, and
`AGENT_TERMINATION_REQUIRED: true`.

The lifecycle event model records created, dispatched, result-received, and
terminated events. Logical termination is mandatory even when the host
environment cannot physically delete the process or chat session.

### runtime taxonomy policy

The runtime taxonomy policy separates durable docs, owner input, and execution
artifacts:

```text
project-docs     = stable documentation
project-runtime  = execution state/artifacts
project-input    = owner input/TZ/upgrade packages
```

`project-runtime/` is runtime evidence, not durable project documentation. The
preferred structure for new runtime-producing work is tasks, worker/audit
results, agent lifecycle events, checkpoints, and reports under typed
subdirectories. Existing legacy runtime layouts remain compatible during the
migration window.

This policy does not itself authorize destructive cleanup. Cleanup requires a
separate bounded task with owner-visible stable evidence, which this release
candidate document provides.

### smoke runner hardening

Governance smoke tests are self-contained local checks. The shell runner uses
temporary local Git repositories and dry-run preflight behavior. The Python
diagnostic wrapper adds fixture discovery, per-fixture status, timeouts,
process-group cleanup, JSON summaries, and per-fixture logs.

The smoke suite is designed to prove blocker behavior for wrong remote, wrong
branch, package-repo project-doc pollution, invalid task packet, push without
accepted lock, secret exposure, approved SSH alias, canonical remote checks,
untracked critical baseline, project-input TZ policy, manual preflight
references, bootstrap/none-route governance, smoke self-containment, coverage
matrix, and version/changelog coherence.

The runner is diagnostic and local. It must not stage, commit, push, contact a
real remote, or require real secrets.

### transactional checkpoint spec status

Transactional checkpoint behavior is specified, not implemented as a mutation
command in v0. The accepted spec defines the future sequence:

```text
preflight -> commit -> push when required -> receipt -> PROJECT_STATE
-> CURRENT_GATE -> TASK_REGISTRY -> NEXT_ACTION -> ACCEPTED_ARTIFACTS
-> event -> post-check verification
```

The authority boundary remains orchestrator-owned. Existing read-only commands,
including `aso lint`, must not perform checkpoint mutation. The v0 status is
therefore documentation/specification complete, implementation pending.

### canonical JSON state preparation status

Canonical JSON state preparation is complete as a migration plan, not active as
runtime authority. In v0, Markdown runtime files remain compatible and
authoritative.

The future target model is:

```text
project-runtime/state/state.json
project-runtime/state/events.jsonl
project-runtime/state/schema.json
```

The plan defines phased migration from Markdown authority to normalized
read-only models, generated JSON snapshots, governed dual-write transition,
canonical JSON authority, and eventual mutation commands. Missing
`project-runtime/state/*` files are not v0 validation errors.

### product capability gates status

Product capability gates are defined as policy. The gate vocabulary is:

```text
governance_pass
task_pass
capability_pass
product_pass
mvp_ready
final_acceptance
```

The policy separates process success from product readiness. A task, scaffold,
lint pass, smoke pass, or governance pass cannot claim MVP readiness or final
acceptance by itself. Capability matrices must remain visible for capability,
product, MVP, and final-acceptance claims.

Current lint behavior includes a conservative skeleton/product guard. Broader
capability matrix enforcement and product gate reporting remain future
tooling work.

### root runtime cleanup decision

The root `project-runtime/` directory is generated workspace execution state.
It may be removed by the dedicated cleanup task after stable release evidence
exists and after the required audit/checkpoint path accepts that cleanup.

This release candidate document is the stable summary required before cleanup.
After root runtime cleanup, owner review should rely on durable package docs,
source files, tests, and this release summary rather than on transient runtime
result dumps.

## known limitations and future backlog

- ASO v0 is read-only. It does not dispatch agents, mutate runtime state,
  create checkpoints, commit, push, or repair findings.
- Transactional checkpoint is a documented future contract, not an implemented
  command.
- Canonical JSON runtime state is planned, but Markdown remains authoritative
  in v0.
- Product capability gate policy is defined, while full matrix enforcement and
  product readiness reporting are queued for future work.
- Runtime taxonomy accepts legacy and preferred layouts during migration, so
  some compatibility warnings can remain until a separate migration task
  resolves them.
- Root runtime cleanup removes transient execution artifacts from the root
  workspace. Durable package evidence must therefore be kept in `agent-system/`
  and other stable project/package documentation.
- Future backlog includes canonical JSON runtime implementation,
  transactional checkpoint implementation, expanded ASO lint strict-mode
  coverage, capability matrix validation, CI coverage for ASO commands and
  smoke diagnostics, and legacy runtime naming migration or documented
  compatibility exceptions.
