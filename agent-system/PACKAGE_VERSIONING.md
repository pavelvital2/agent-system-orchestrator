# PACKAGE_VERSIONING

## Purpose

This document defines minimal package versioning policy for the universal orchestration package. It is not a release manifest and does not list every artifact.

## Runtime version fields

Mandatory runtime version fields:

```text
PACKAGE_VERSION:
GOVERNANCE_RULESET_VERSION:
RUNTIME_SCHEMA_VERSION:
```

`PROJECT_STATE.md` must contain these fields and reference the active values unless a governed migration task explicitly changes them.

## Active version constants

```text
CURRENT_PACKAGE_VERSION: 3.7.7
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.7
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
```

These constants define the active package/governance/schema tuple for runtime validation. They are policy constants, not a release manifest.

## Correction semantics

Owner-authorized corrections may reconcile internally inconsistent artifacts
inside an accepted package version when the intended public package capability
is already installed. Such corrections are recorded in `GOVERNANCE_CHANGELOG.md`
and must state whether the active tuple changed.

The v1.2.0 correction chain keeps the active tuple unchanged:

```text
CURRENT_PACKAGE_VERSION: 1.2.0
CURRENT_GOVERNANCE_RULESET_VERSION: 1.2.0
CURRENT_RUNTIME_SCHEMA_VERSION: 1.1.0
```

Runtime file set synchronization, role/task enum synchronization, RESULT field
normalization, documentation stage reconciliation, and final smoke/cross-link
hardening in that chain are treated as v1.2.0 correction metadata, not as a new
package installation.

These correction entries do not reserve or pre-install any future minor package
version. A later package installation must use its own owner-authorized bounded
package update, active tuple change, migration note, and changelog entry.

The v1.3.0 feature upgrade installs:

```text
CURRENT_PACKAGE_VERSION: 1.3.0
CURRENT_GOVERNANCE_RULESET_VERSION: 1.3.0
CURRENT_RUNTIME_SCHEMA_VERSION: 1.2.0
```

This upgrade adds Research Dependency Loop, Design Research Loop, Requester
Return Protocol, explicit reasoning-level governance, requester return metadata
fields, and runtime tuple cleanup for `CURRENT_GATE.ACTION_SEMANTIC` and
`NEXT_ACTION.ACTION_SEMANTIC`. It must not use `1.2.1` as the active tuple.

The v2.0.0 governance hardening package installs:

```text
CURRENT_PACKAGE_VERSION: 2.0.0
CURRENT_GOVERNANCE_RULESET_VERSION: 2.0.0
CURRENT_RUNTIME_SCHEMA_VERSION: 2.0.0
```

This major update makes workspace identity validation and repository lock
validation mandatory before profile-agent dispatch, runtime initialization,
checkpoint, commit, or push. Existing runtime states that lack the mandatory
workspace identity, repository lock, or checkpoint eligibility fields enter
correction or owner wait flow; the orchestrator must not silently infer those
fields from folder name, inherited `.git` metadata, or raw remote strings.

The governance smoke-test addition for
`TASK_ASO_PATCH_008_GOVERNANCE_SMOKE_TESTS` keeps the active tuple unchanged at
`2.0.0 / 2.0.0 / 2.0.0`. It adds deterministic local fixtures and a dry-run
runner for the v2.0.0 blocker surface; it is recorded in
`GOVERNANCE_CHANGELOG.md` and does not install a new package version.

The v3.0.0 ASO control-plane v0 release candidate installs:

```text
CURRENT_PACKAGE_VERSION: 3.0.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.0.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

This major update introduces the experimental read-only ASO helper CLI and
requires explicit package/workspace mode selection for package repository and
target workspace validation. Package repository cleanup policy treats root
generated workspace artifacts as non-package state: root
`project-runtime/`, `project-input/`, and `project-archive/` are not shipped as
tracked package state, while target workspaces may still generate runtime
state under `project-runtime/`.

The v3.0.0 package records canonical worker result and audit result paths,
profile-agent lifecycle invariants, reasoning-level authority, and design-role
authority:

```text
profile agent lifecycle: one agent = one task = one RESULT = terminate
REASONING_LEVEL values: low, medium, high, xhigh
canonical design role: solution_architect
deprecated compatibility alias: designer
```

Design output is governed by the solution architect output contract and review
rubric. Smoke runner hardening, transactional checkpoint specification,
canonical JSON state migration preparation, and product capability gate
vocabulary are part of the accepted v3.0.0 package surface.

v3.0.0 is a major version because it changes or introduces mandatory lifecycle
semantics, role authority and canonical role naming, filesystem and package
repository authority, runtime artifact taxonomy, and package/workspace
validation mode.

Migration note: existing target project workspaces are not automatically
cleaned. Root `project-runtime/`, `project-input/`, and `project-archive/` are
ignored only in the package repository. Target workspaces may continue
generating `project-runtime/` as runtime state. Existing v2.0.0 workspaces must
install or update `agent-system/` to v3.0.0 before relying on ASO
package/workspace mode.

The v3.0.1 package/governance coherence patch installs:

```text
CURRENT_PACKAGE_VERSION: 3.0.1
CURRENT_GOVERNANCE_RULESET_VERSION: 3.0.1
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

This patch updates package documentation, current examples, release evidence,
governance changelog enum usage, lifecycle wording, smoke checks, and secret
ignore patterns after the accepted v3.0.0 release. It does not change runtime
schema sidecars, ASO v0 command scope, or the read-only ASO helper boundary.

The Stage 1 executable-controls documentation and changelog cleanup records the
current local command surface without changing active version constants:

```text
CURRENT_PACKAGE_VERSION: 3.0.1
CURRENT_GOVERNANCE_RULESET_VERSION: 3.0.1
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

This bounded cleanup documents local installation, root Make targets, package
and workspace doctor usage, design validation, context-pack validation,
CI/smoke expectations, publication boundaries, and final validation report
handoff. It preserves the active tuple because this task is limited to package
documentation/release paths and cannot update `pyproject.toml` or the wrapper
package `__version__`. Keeping the tuple unchanged preserves doctor alignment
with the installed package metadata and does not change runtime schema
authority. Any future package version bump must update
`CURRENT_PACKAGE_VERSION`, `pyproject.toml`, and
`agent_system_orchestrator_aso.__version__` in one audited package update.

The Stage 2 state-contract correction installs:

```text
CURRENT_PACKAGE_VERSION: 3.0.2
CURRENT_GOVERNANCE_RULESET_VERSION: 3.0.2
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

This patch resolves Stage 2 drift among runtime state sidecar templates,
schemas, fixtures, validator expectations, command examples, and release
evidence. It keeps the runtime schema version at `3.0.0` because the correction
reconciles the accepted Stage 2 state contract rather than introducing a new
runtime state meaning. It also preserves the read-only ASO helper boundary:
ASO does not dispatch agents, mutate package or workspace state, perform
checkpoints, commit, or push.

The Stage 3 safe automation diagnostics package installs:

```text
CURRENT_PACKAGE_VERSION: 3.1.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.1.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

This minor update adds package synchronization diagnostics and release cleanup
documentation while preserving the runtime schema version at `3.0.0`.
Stage 3 command surfaces are read-only, dry-run, or proposal-only. They may
inspect package metadata, command readiness, generated reports, and cleanup
eligibility, but they do not dispatch agents, mutate package or workspace
state, perform governed checkpoints, approve owner decisions, commit, push, or
publish local input/runtime/archive roots.

The Stage 3 DAG checkpoint correction package installs:

```text
CURRENT_PACKAGE_VERSION: 3.1.1
CURRENT_GOVERNANCE_RULESET_VERSION: 3.1.1
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

This patch resolves `ASO-STAGE3-AUDIT-BLOCKER-001` by recording the accepted
Stage 3 governance state through the DAG checkpoint correction branch and its
Task 005 validation report. It keeps the runtime schema at `3.0.0` because the
correction clarifies checkpoint dependency semantics and documentation
authority rather than changing runtime state meaning.

Stage 3 remains read-only, dry-run, or proposal-only. `audit_passed` is not a
satisfied dependency for downstream readiness; dependency completion requires
`checkpoint_done` with checkpoint evidence, or another explicitly completed
terminal state allowed by the governance rules. This documentation/version
correction does not claim the final correction pass before Task 005 supplies
command evidence.

The Stage 3 pre-main package layout cleanup installs:

```text
CURRENT_PACKAGE_VERSION: 3.1.2
CURRENT_GOVERNANCE_RULESET_VERSION: 3.1.2
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

This patch makes the installable ASO package canonical under
`agent-system/tools/aso/agent_system_orchestrator_aso/` and removes the former
root duplicate package path from the governed package layout. It keeps the
runtime schema at `3.0.0` because the cleanup changes repository package
layout, installation ergonomics, and verification evidence rather than accepted
runtime state meaning.

Package discovery in `pyproject.toml` points to `agent-system/tools/aso`.
Package-layout verification replaces duplicate copy synchronization as the
current package-source coherence check. Final validation evidence for this
cleanup must record command evidence without claiming an unknowable final
commit before the orchestrator-owned checkpoint and push. Merge readiness must
follow `09_MAIN_MERGE_READINESS_PROCEDURE.md` or accepted package
merge-readiness docs after audit, checkpoint, push, and remote CI evidence.

The ASO Project Factory P0 package installs:

```text
CURRENT_PACKAGE_VERSION: 3.2.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.2.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

This minor update adds local generated-project creation, `aso.lock`, generated
project clean-repository verification, installation bootstrap improvements,
and Project Factory release documentation. It keeps the runtime schema at
`3.0.0` because it adds package CLI/product capability without changing the
accepted meaning of runtime state.

The ASO Project Factory P1 package installs:

```text
CURRENT_PACKAGE_VERSION: 3.3.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.3.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

This minor update adds Project Factory GitHub publication planning,
reference-mode generated projects, and the package wizard capability surface.
It keeps the runtime schema at `3.0.0` because it does not change the accepted
meaning of runtime state.

The ASO Runtime State P2 package installs:

```text
CURRENT_PACKAGE_VERSION: 3.4.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.4.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
```

This minor update defines the JSON-first runtime state foundation under
`project-runtime/state/` while preserving the Project Factory P1 safety
boundary. Runtime schema `3.1.0` is the target P2 schema for current sidecar
envelopes and schema manifests. Existing P1 and P0 generated-project lockfiles
remain compatible where their publication boundary and engine metadata satisfy
the accepted compatibility rules. P2 does not install a runtime daemon, live
agent dispatch, proposal/apply mutation layer, checkpoint executor,
distributed workers, or external queue infrastructure.

The ASO Safe Proposal / Apply P3 package installs:

```text
CURRENT_PACKAGE_VERSION: 3.5.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.5.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
```

This minor update defines proposal/apply as a bounded local runtime-state
automation layer while preserving Runtime Schema `3.1.0`. P3 may create
proposal, receipt, and report artifacts under `project-runtime/proposals/`,
`project-runtime/receipts/`, and `project-runtime/reports/`; those roots remain
local runtime artifacts and must not be published from the package repository
or generated-project publication flows. P3 does not install a runtime daemon,
live agent dispatch, checkpoint executor, commit/push automation, distributed
workers, web control panel, or multi-project registry. P4 dashboard/control
plane work, P5 queue/dispatcher work, P6 checkpoint executor work, daemon mode,
and distributed workers are deferred to later bounded package upgrades.

The corrected ASO Project Design Gap Governance P4 package installs:

```text
CURRENT_PACKAGE_VERSION: 3.6.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.6.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

This minor update defines the authoritative designer-led project design and
gap governance contract while preserving Runtime Schema `3.1.0`. ASO remains a
deterministic governance/control conveyor: it validates artifacts, gates
transitions, routes audited owner questions, records receipts, and audits
process shape. ASO does not semantically read TZ, replace project designer or
requirements analyst reasoning, generate product questions from TZ content,
ask owners to choose implementation technologies, add product-intake code, or
install a daemon, live dispatch, checkpoint executor, product generator,
external worker system, or secret collection flow.

The branch `upgrade/product-intake-capability-p4-v3.6.0` is superseded and
non-authoritative. It may remain in remote history but must not be merged as
the corrected P4 line. The authoritative branch is
`upgrade/project-design-gap-governance-p4-v3.6.0`.

The ASO Hotfix Workspace Bootstrap / Runtime Materialization / Agent Lifecycle
P4.1 package installs:

```text
CURRENT_PACKAGE_VERSION: 3.6.1
CURRENT_GOVERNANCE_RULESET_VERSION: 3.6.1
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

This patch documents the P4.1 hotfix boundary while preserving Runtime Schema
`3.1.0`. P4.1 fixes workspace/package mode guard handling, derived runtime
Markdown view materialization from JSON sidecars, and the required agent
lifecycle termination event after RESULT before audit routing. It does not
change the P2/P3 sidecar envelope, semantically read raw TZ, replace the
project designer or requirements analyst, install product-intake code, add a
daemon, live dispatch, checkpoint executor, product-intake engine, product
generator, external worker system, or secret collection flow.

The ASO Artifact Package Model P5 package installs:

```text
CURRENT_PACKAGE_VERSION: 3.7.1
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.1
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

This minor update defines the artifact package model contract and version
boundary while preserving Runtime Schema `3.1.0`. P5 separates publishable
package artifacts from workspace-local runtime/input/archive roots and
formalizes artifact package schema version `1.1.0` for packaged instruction,
template, validator, role, lifecycle, profile, example, release, and tool
artifacts. It does not migrate active `project-runtime/` state, redefine the
P2/P3 runtime sidecar envelope, install a daemon, dispatch live agents,
execute checkpoints, publish generated workspaces, or broaden proposal/apply
mutation authority.

The ASO Bootstrap State Reconciliation P5.2 correction installs:

```text
CURRENT_PACKAGE_VERSION: 3.7.2
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.2
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

This patch corrects bootstrap state reconciliation while preserving Runtime
Schema `3.1.0` and Artifact Package Schema `1.1.0`. P5.2 makes active/open
bootstrap state incompatible with terminal STOP when mandatory bootstrap inputs
exist, requires `PROJECT_STATE.TZ_PATH` to reference a project TZ file rather
than an IANA timezone string, treats missing derived Markdown runtime views as
materialization or repair blockers, and keeps `plan-next` on a bootstrap
preparation/correction route instead of reporting misleading terminal
readiness. It does not redefine the P2/P3 sidecar envelope, semantically read
raw TZ content, replace project designer or requirements analyst reasoning,
install a daemon, dispatch live agents, execute checkpoints, publish generated
workspaces, or broaden proposal/apply mutation authority.

The ASO Bootstrap TASK_REGISTRY Alignment P5.3 correction installs:

```text
CURRENT_PACKAGE_VERSION: 3.7.3
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.3
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

This patch aligns TASK_REGISTRY task-kind documentation and runtime schema
metadata so `bootstrap` is an allowed governed task kind for the first
bootstrap route and governed bootstrap correction tasks. Unknown task kinds
remain forbidden. Artifact Package Schema `1.1.0` is preserved, and P5.3 does
not change artifact package storage semantics, dispatch live agents, execute
checkpoints, publish generated workspaces, or broaden proposal/apply mutation
authority.

The ASO Planner Dispatchability Gate P5.4 correction installs:

```text
CURRENT_PACKAGE_VERSION: 3.7.4
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.4
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

This patch defines the planner dispatchability boundary: `CREATE_AGENT` is
valid only when a dispatchability gate proves the current next action can
dispatch a profile agent. The gate must reject control roles such as
`orchestrator` or `owner`, missing or `NONE` task ids, missing or `NONE` task
packets, invalid or absent task packet files, incompatible task registry
entries, blocking rules, failed workspace identity or repository lock checks,
and any current gate state that forbids dispatch. When the gate fails,
`plan-next` must return a documented non-dispatch route such as
`CORRECTION_REQUIRED`, `UPDATE_STATE`, `ASK_OWNER`, `FREEZE`,
`BOOTSTRAP_PREP`, or `STOP` with machine-readable reasons. Runtime Schema
`3.1.1` and Artifact Package Schema `1.1.0` are preserved. P5.4 does not add a
daemon, live dispatch executor, checkpoint executor, ASO Studio, distributed
workers, or automatic task execution.

The ASO Working State Stabilization P5.5 correction installs:

```text
CURRENT_PACKAGE_VERSION: 3.7.5
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.5
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

This patch aligns active package/governance version metadata, cross-link
readiness documentation, and the governance rule registry with the accepted
P5.4/P5.5 planner dispatchability boundary. Runtime Schema `3.1.1` and
Artifact Package Schema `1.1.0` are preserved. P5.5 does not change planner
implementation, runtime sidecar envelopes, artifact package schema, live
dispatch authority, checkpoint execution, daemon behavior, or artifact package
storage semantics.

The ASO Real-TZ E2E Install and Intake P5.6 correction installs:

```text
CURRENT_PACKAGE_VERSION: 3.7.6
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.6
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

This patch records the accepted real-TZ installed-orchestrator workflow and
release validation evidence. P5.6 keeps Runtime Schema `3.1.1` and Artifact
Package Schema `1.1.0`; it does not change runtime sidecar envelopes, add
product generation, dispatch live agents, execute checkpoints, install a
daemon, or collect secrets.

The ASO P5.6 audit hardening correction installs:

```text
CURRENT_PACKAGE_VERSION: 3.7.7
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.7
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

This patch closes audit fixes 010 through 080 for installed-resource test
hygiene, source contamination guarding, clean install semantics, intake render
synchronization, bootstrap candidate artifact output, status enum authority,
CI E2E hardening, and final release validation docs. It validates ASO workflow
readiness through real-TZ bootstrap and read-only plan-next dispatchability
only; it does not claim full real-product Telegram bot generation.

## Version semantics

```text
PATCH  = wording, formatting, or non-semantic clarification
MINOR  = compatible hardening; new validation or fields that do not change accepted state meaning
MAJOR  = changes to mandatory transitions, role authority, filesystem authority, terminal semantics, required runtime files, or status meanings
```

## Package update rules

1. Universal package changes occur only through owner-authorized bounded package update task.
2. Normal project agents cannot change `agent-system/`.
3. Package update activates governance freeze for normal project dispatch.
4. Runtime schema, templates, runtime loop, and governance docs in the compatibility set must be compatible before freeze exits.
5. Package change must be recorded in `GOVERNANCE_CHANGELOG.md`.
6. Existing project runtime state that lacks newly mandatory fields enters correction/wait flow, not silent inference.

## Compatibility rule

A package version is valid only when the compatibility set is mutually compatible for the active package version, governance ruleset version, and runtime schema version.

The compatibility set includes at minimum:

```text
RUNTIME_STATE_SCHEMA.md
PROJECT_STATE_TEMPLATE.md
CURRENT_GATE_TEMPLATE.md
NEXT_ACTION_TEMPLATE.md
GAP_REGISTER_TEMPLATE.md
AGENT_RESULTS_LOG_TEMPLATE.md
ORCHESTRATOR_RUNTIME_LOOP.md
ALLOWED_ORCHESTRATOR_ACTIONS.md
FILESYSTEM_GOVERNANCE.md
GOVERNANCE_AUTHORITY.md
STATE_TRANSITION_RULES.md
VIOLATION_RECOVERY.md
ACCEPTED_STATE_LOCKING.md
```
