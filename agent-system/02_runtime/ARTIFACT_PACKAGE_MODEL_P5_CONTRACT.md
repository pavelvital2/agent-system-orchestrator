# ARTIFACT_PACKAGE_MODEL_P5_CONTRACT

## Purpose

This document defines the P5 artifact package model boundary for ASO package
version `3.7.0`, governance ruleset version `3.7.0`, Runtime Schema version
`3.1.0`, design/gap governance schema version `1.0.0`, and artifact package
schema version `1.0.0`.

P5 is a version-boundary and packaging-governance update. It preserves the
P2/P3 Runtime Schema `3.1.0` sidecar envelope and does not migrate active
`project-runtime/` state.

## Artifact Package Schema

Artifact package schema `1.0.0` defines the publishable ASO package artifact
classes and their boundary from workspace-local state. It covers packaged
instruction, role, runtime contract, template, validator, lifecycle, profile,
gap-flow, log-template, example, release-evidence, factory-contract, script,
and ASO helper tool artifacts under `agent-system/`.

The artifact package schema is package metadata. It is not a runtime sidecar
schema and must not be used as the value for Runtime Schema fields. Runtime
sidecars continue to use Runtime Schema `3.1.0`.

## Publishable Package Artifacts

P5 treats these package-relative roots as publishable package artifacts when
they are intentionally tracked:

```text
agent-system/00_start/
agent-system/01_roles/
agent-system/02_runtime/
agent-system/03_templates/
agent-system/04_state/
agent-system/05_gap_flow/
agent-system/06_logs/
agent-system/07_lifecycle/
agent-system/08_profiles/
agent-system/09_validators/
agent-system/10_examples/
agent-system/11_release/
agent-system/12_project_factory/
agent-system/scripts/
agent-system/tests/
agent-system/tools/
agent-system/README.md
agent-system/PACKAGE_VERSIONING.md
agent-system/GOVERNANCE_CHANGELOG.md
README.md
README_INSTALL.md
install.sh
install.ps1
Makefile
pyproject.toml
```

The package model is conservative: adding a new publishable root requires a
later bounded package update with audit evidence.

## Workspace-Local Boundary

These roots are workspace-local and must not be treated as publishable package
artifacts from the package repository root:

```text
project-input/
project-runtime/
project-archive/
.venv/
```

Generated projects may contain these roots as ignored local workspace state.
Their existence in a target workspace does not make them package artifacts.

## Metadata Boundary

The active package metadata tuple is:

```text
CURRENT_PACKAGE_VERSION: 3.7.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.0.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

The artifact package schema version may advance independently of Runtime
Schema only through a governed package update. Runtime Schema remains `3.1.0`
until an explicit runtime schema contract update changes it.

## Authority Boundary

ASO may validate package artifact boundaries, package version metadata,
schema references, lockfile compatibility, and publication-root exclusions.

ASO must not:

- migrate active `project-runtime/` state as part of this P5 boundary;
- redefine the P2/P3 Runtime Schema `3.1.0` sidecar envelope;
- treat `project-input/`, `project-runtime/`, `project-archive/`, or `.venv/`
  as publishable package roots;
- install product-intake code or a product-intake engine;
- run a daemon;
- dispatch live agents;
- execute checkpoints;
- commit, push, or publish without a later governed flow;
- generate products;
- run external workers or distributed queue infrastructure;
- collect secrets.

## Compatibility

Existing P4.1 package metadata and generated-project lockfiles remain
compatible when they satisfy the accepted engine tuple rules. P5 makes
`3.7.0 / 3.1.0` the active engine tuple and keeps earlier accepted tuples as
explicit compatibility cases.

Runtime Schema `3.1.0` remains the canonical sidecar schema for current
runtime state. P5 adds artifact package schema metadata and package-boundary
documentation only; it does not silently migrate workspaces or broaden
proposal/apply mutation authority.
