# PROPOSAL_APPLY_P3_CONTRACT

## Purpose

Safe Proposal / Apply P3 defines a bounded local runtime-state automation
layer for ASO package version `3.5.0`, governance ruleset version `3.5.0`,
and runtime schema version `3.1.0`.

P3 does not redefine the Runtime Schema `3.1.0` sidecar envelope. It adds a
governed proposal and receipt boundary around local runtime-state changes so
operators can review deterministic plans before any confirmed mutation.

## Authority Boundary

Proposal/apply is local runtime-state automation only. The governed flow is:

```text
state verify -> propose -> review -> apply dry-run -> apply confirmed -> receipt -> state verify
```

Proposal creation may describe candidate changes, validation requirements,
staleness checks, and human-readable impact. Confirmed apply may perform only
validated runtime-state mutations that were already represented in a proposal,
and it must emit a receipt.

P3 commands must fail closed when proposal base hashes, workspace identity,
repository lock state, schema compatibility, or path allowlists do not match
the current workspace.

## Allowed Runtime Artifact Roots

Proposal/apply runtime artifacts are workspace-local and unpublished:

```text
project-runtime/proposals/
project-runtime/receipts/
project-runtime/reports/
```

Proposal creation may write only proposal artifacts under:

```text
project-runtime/proposals/
```

Confirmed apply may write only:

```text
project-runtime/state/*.json
project-runtime/receipts/*.json
project-runtime/reports/*.json
```

Package repository files are not writable by workspace proposal/apply
commands. Active proposal, receipt, and report artifacts are runtime artifacts
and must not be published from `project-runtime/`.

## Proposal Artifacts

A proposal artifact records a deterministic candidate action before mutation.
It must identify at least:

```text
proposal_id
proposal_type
schema_version
package_version
runtime_schema_version
created_at
created_by
target_root
target_workspace_identity
base_state_hashes
required_validators
operations
safety_class
status
human_summary
```

Allowed safety classes are:

```text
runtime_state_only
checkpoint_proposal_only
read_only_plan
```

Checkpoint proposals may record eligibility evidence only. They must not
perform checkpoint execution, commits, pushes, or repository publication.

## Apply Receipts

An apply receipt records the exact confirmed result. It must identify at least:

```text
receipt_id
proposal_id
proposal_type
schema_version
package_version
runtime_schema_version
applied_at
applied_by
target_root
validators_passed
base_state_hashes
result_state_hashes
applied_operations
outcome
```

Receipts are evidence, not authority to commit or publish. A receipt may be
used by later validators, dashboards, or checkpoint tooling, but it does not
grant those tools execution rights.

## Required Validation Model

Confirmed apply must run the governed validator chain before and after
mutation. The minimum chain is:

```text
proposal schema validation
state verify before apply
workspace identity check
repository lock check when present
base hash/staleness check
operation path allowlist check
state verify after apply
receipt validation
publication boundary check
```

State writes must use deterministic JSON formatting and atomic replacement
where practical. Partial sidecars or partial receipts must not be left behind
after a failed apply.

## Non-Goals

P3 explicitly does not implement or authorize:

```text
runtime daemon
live agent dispatch
checkpoint executor
commit/push automation
distributed workers
web control panel
multi-project registry
```

Those capabilities require later bounded package upgrades with their own
contracts, validators, audits, and publication-boundary evidence.

## Compatibility

Runtime Schema `3.1.0` remains the canonical P2/P3 sidecar schema. P3 may add
proposal and receipt artifact schemas, templates, fixtures, tests, and CLI
surfaces, but those artifacts do not redefine P2 sidecar authority.

Existing P0/P1/P2 behavior remains governed by its accepted compatibility
rules. P3 adds proposal/apply safety around local runtime state; it does not
silently migrate workspaces or broaden publication authority.
