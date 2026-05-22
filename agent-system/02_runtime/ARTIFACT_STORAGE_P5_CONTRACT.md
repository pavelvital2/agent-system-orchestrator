# ARTIFACT_STORAGE_P5_CONTRACT

## Purpose

This contract defines the P5 workspace-local artifact storage model for raw
artifacts, candidate artifacts, accepted artifacts, and rejected artifacts.

It applies to ASO package version `3.7.0`, governance ruleset version `3.7.0`,
Runtime Schema version `3.1.0`, and Artifact Package Schema version `1.0.0`.

This contract does not create CLI accept/reject/render/list commands, lifecycle
integration, context-pack integration, checkpoint execution, commit behavior,
push behavior, daemon behavior, live dispatch, or product-intake behavior.

## Storage Roots

The governed artifact storage roots are workspace-local runtime paths:

```text
project-runtime/artifacts/raw/
project-runtime/artifacts/candidates/
project-runtime/artifacts/accepted/
project-runtime/artifacts/rejected/
```

These roots are not publishable ASO package roots. They remain excluded from
tracked package publication by the P5 package boundary, together with
`project-input/`, `project-runtime/`, `project-archive/`, and `.venv/`.

## Storage Classes

`raw` stores captured source material exactly as submitted or received. Raw
artifact content is evidence, not accepted project truth.

`candidates` stores normalized or structured candidate packages derived from
raw input or agent output. Candidate artifacts are reviewable proposals, not
accepted project truth.

`accepted` stores immutable accepted artifact records after a governed
acceptance decision. Acceptance records must reference their candidate and
source evidence.

`rejected` stores immutable rejected artifact records after a governed rejection
decision. Rejection records must reference their candidate and source evidence
and must preserve the rejection rationale or evidence reference.

## Raw To Candidate To Accepted Or Rejected Flow

The storage model is append-only:

```text
raw -> candidates -> accepted
raw -> candidates -> rejected
```

The flow records classification. It must not mutate or delete the prior raw or
candidate artifact. Accepted and rejected records are new immutable records that
refer back to their evidence chain.

The P5 storage model only defines paths and expectations. A later governed task
may add CLI commands or lifecycle integration for submitting, validating,
accepting, rejecting, rendering, or listing artifacts.

## Safe Path Requirements

Artifact storage helpers must construct workspace-relative POSIX paths under
one of the governed storage roots. Helpers must reject:

- absolute paths;
- parent traversal such as `..`;
- empty member paths;
- current-directory path segments;
- backslash-separated paths;
- NUL bytes;
- unknown storage buckets.

The canonical helper implementation is:

```text
agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/artifact_storage.py
```

The helper is intentionally path-only. It must not create directories, write
files, accept artifacts, reject artifacts, mutate runtime state, or integrate
with lifecycle/context-pack flows.

## Immutability Expectations

All four P5 storage classes are immutable after materialization.

Raw artifacts preserve source evidence. Candidate artifacts preserve the exact
candidate version reviewed. Accepted artifacts preserve the exact accepted
record and evidence chain. Rejected artifacts preserve the exact rejected
record, evidence chain, and rejection rationale.

Corrections must create a new artifact record instead of overwriting an
existing raw, candidate, accepted, or rejected artifact.

## Runtime Schema Boundary

This contract does not migrate Runtime Schema `3.1.0` and does not add a new
runtime sidecar. Existing Runtime Schema `3.1.0` state remains governed by:

```text
agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json
```
