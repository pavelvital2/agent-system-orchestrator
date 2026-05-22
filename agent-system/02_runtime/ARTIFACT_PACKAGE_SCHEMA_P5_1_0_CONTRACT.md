# ARTIFACT_PACKAGE_SCHEMA_P5_1_0_CONTRACT

## Purpose

This contract defines the Artifact Package Schema `1.0.0` structured
contracts for ASO package version `3.7.0`, governance ruleset version `3.7.0`,
and Runtime Schema version `3.1.0`.

Artifact Package Schema `1.0.0` is package metadata. It does not redefine the
Runtime Schema `3.1.0` sidecar envelope and does not create artifact CLI
commands, package storage, lifecycle mutation, dispatch, checkpoint execution,
commit, push, or publication behavior.

The separate P5 workspace-local storage contract is:

```text
agent-system/02_runtime/ARTIFACT_STORAGE_P5_CONTRACT.md
```

That contract defines `project-runtime/artifacts/raw/`,
`project-runtime/artifacts/candidates/`,
`project-runtime/artifacts/accepted/`, and
`project-runtime/artifacts/rejected/` as runtime workspace-local storage roots.
Those roots are not publishable package artifacts and are not Runtime Schema
sidecars.

## Schema Files

The active P5 schema files are:

```text
agent-system/09_validators/schemas/artifact_package_manifest.schema.json
agent-system/09_validators/schemas/result_package.schema.json
agent-system/09_validators/schemas/audit_result_package.schema.json
agent-system/09_validators/schemas/structured_artifact.schema.json
```

The matching package templates are:

```text
agent-system/03_templates/artifact_package_manifest.template.json
agent-system/03_templates/result_package.template.json
agent-system/03_templates/audit_result_package.template.json
agent-system/03_templates/structured_artifact.template.json
```

## Version Fields

P5 RESULT package, AUDIT_RESULT package, and shared structured artifact schemas
require:

```text
schema_version: 1.0.0
package_version: 3.7.0
governance_ruleset_version: 3.7.0
runtime_schema_version: 3.1.0
artifact_package_schema_version: 1.0.0
```

`artifact_package_manifest.schema.json` is excluded from that shared version
tuple. The canonical manifest carries only `artifact_package_schema_version:
1.0.0` plus the manifest fields defined by its schema:

```text
artifact_type
artifact_id
task_id
role
attempt_no
status
main_document
structured_artifacts
evidence_refs
created_at
producer
```

`runtime_schema_version` is recorded only as the active engine tuple value. It
does not make these package artifacts Runtime Schema sidecars.

## Artifact Package Manifest

`artifact_package_manifest.schema.json` records canonical package manifest
metadata: artifact class, package-relative artifact paths, evidence references,
producer identity, and excluded workspace-local path roots. The canonical
manifest schema rejects fields outside that manifest contract.

The manifest schema excludes these roots from package artifact paths:

```text
project-input/
project-runtime/
project-archive/
.venv/
```

The manifest schema must remain conservative. Adding a publishable root or a
new artifact class requires a later governed package update with audit
evidence.

## RESULT Package

`result_package.schema.json` defines a structured envelope for profile-agent
RESULT evidence. It preserves the RESULT lifecycle constants:

```text
reuse_allowed: false
agent_termination_required: true
```

`result_ref` identifies the governed worker RESULT path shape:

```text
project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_<N>.md
```

This schema does not create that storage location and does not record or route
the result. It only defines the structured package contract.

## AUDIT_RESULT Package

`audit_result_package.schema.json` defines a structured envelope for auditor
AUDIT_RESULT evidence. It preserves the audit RESULT lifecycle constants:

```text
reuse_allowed: false
agent_termination_required: true
```

`audit_result_ref` identifies the governed audit RESULT path shape:

```text
project-runtime/results/audit/AUDIT_RESULT_<TASK_ID>_ATTEMPT_<N>.md
```

`audited_result_ref` identifies the worker RESULT that was audited. The schema
requires the mandatory audit check labels from
`agent-system/03_templates/AGENT_RESULT_TEMPLATE.md`.

This schema does not authorize checkpoint execution, commit, push, publication,
or state mutation.

## Shared Structured Artifacts

`structured_artifact.schema.json` defines a minimal shared envelope for
package-local structured artifacts. It carries source references, typed
content, validation status, and the shared P5 version tuple.

Shared structured artifacts are package metadata only. Runtime state remains
under the Runtime Schema `3.1.0` sidecar contract.
