# Contract Authority Map

This map identifies the active P5-family contract authority for the ASO
package. It prevents later correction tasks from creating parallel authority
for the same runtime, artifact, bootstrap, or planner contract surface.

## Active P5 Authority Chain

| Package phase | Active authority | Authority scope | Override relationship |
| --- | --- | --- | --- |
| P5 | `ARTIFACT_PACKAGE_MODEL_P5_CONTRACT.md` | Introduces the governed artifact package model and accepted-artifact boundary. | Base P5 artifact storage authority. |
| P5.1 | `ARTIFACT_PACKAGE_MODEL_P5_1_CORRECTION_CONTRACT.md` and `ARTIFACT_PACKAGE_SCHEMA_P5_1_0_CONTRACT.md` | Corrects artifact package model details and defines Artifact Package Schema `1.1.0`. | Overrides P5 where the correction/schema contract is more specific. |
| P5.2 | `BOOTSTRAP_STATE_RECONCILIATION_P5_2_CONTRACT.md` | Defines bootstrap state reconciliation and contradictory-state handling. | Overrides earlier bootstrap-readiness interpretation only. |
| P5.3 | `RUNTIME_STATE_P2_CONTRACT.md` plus `runtime_state_3_1_0.contract.json` | Keeps the Runtime State sidecar envelope authority while advancing active runtime metadata to Runtime Schema `3.1.1`. | Updates runtime schema metadata and task-kind alignment without replacing the P2 envelope contract. |
| P5.4 | `PLANNER_DISPATCHABILITY_GATE_P5_4_CONTRACT.md` | Defines the planner Dispatchability Gate, including profile-role dispatchability and non-dispatch control actions. | Adds planner gate authority; does not change runtime sidecar envelopes or artifact package storage. |
| P5.5 | Historical package metadata and validator/readiness documentation | Stabilizes active authority references and CI/package smoke coverage. | Clarifies existing authority only; does not add runtime semantics, daemon mode, live dispatch, checkpoint execution, or duplicate contract files. |
| P5.6 | Historical package metadata, release validation docs, installed real-TZ workflow docs, and audit hardening evidence | Records real-TZ installed-orchestrator validation, safe install/intake operator guidance, source hygiene, clean install semantics, and CI E2E smoke coverage. | Documentation, metadata, test, and validation hardening only; does not add runtime semantics, daemon mode, live dispatch, checkpoint execution, product generation, or duplicate contract files. |
| P57 | Package metadata `3.7.8`, this map, runtime authority documentation, and state render write-boundary documentation | Aligns active package/governance authority and removes runtime source-of-truth contradictions. | Documentation and metadata authority sync only; Runtime Schema `3.1.1` and Artifact Package Schema `1.1.0` are preserved. |

## Runtime Schema Contract File Authority

Runtime Schema `3.1.1` continues to use the packaged contract file:

```text
agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json
```

The filename is historical: the base JSON sidecar envelope was introduced for
the P2/P3 Runtime State `3.1.0` boundary. The contract document itself now
declares `contract_id: ASO_RUNTIME_STATE_SCHEMA_3_1_1` and
`runtime_schema_version: 3.1.1`, and the ASO runtime contract helper exposes
that same file as the active contract path for Runtime Schema `3.1.1`.

Do not add a second `runtime_state_3_1_1.contract.json` file unless a later
governed migration explicitly replaces this authority map. A duplicate file
with equivalent envelope rules would create ambiguous authority. If a future
runtime schema changes the envelope or sidecar contract semantics, the new
contract file must name which prior authority it supersedes and update this
map in the same change.

## Current Version Tuple

The active P57 tuple is:

```text
package_version: 3.7.8
governance_ruleset_version: 3.7.8
runtime_schema_version: 3.1.1
artifact_package_schema_version: 1.1.0
```

This tuple is metadata and validation authority only. It does not authorize
runtime mutation, profile-agent dispatch, daemon execution, checkpoint
execution, publication, or workspace state migration.

The active P57 tuple supersedes prior P5.6 package/governance baselines without
changing Runtime Schema `3.1.1` or Artifact Package Schema `1.1.0`.
