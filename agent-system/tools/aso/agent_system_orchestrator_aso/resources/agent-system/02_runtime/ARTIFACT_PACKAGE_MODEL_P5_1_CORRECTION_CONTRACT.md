# ARTIFACT_PACKAGE_MODEL_P5_1_CORRECTION_CONTRACT

## Version Boundary

P5.1 is the corrective artifact package model for the ASO package.

```text
PACKAGE_VERSION: 3.7.1
GOVERNANCE_RULESET_VERSION: 3.7.1
RUNTIME_SCHEMA_VERSION: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
```

Runtime Schema `3.1.0` is preserved. Artifact Package Schema `1.1.0`
changes package path semantics and accept/reject behavior only.

## Corrections

- Bootstrap task packets use the canonical `# TASK PACKET` marker with
  `TASK_KIND: bootstrap`.
- Artifact package manifests are stored in self-contained package directories.
- Manifest file references are package-relative and must not escape the package
  root.
- Artifact accept/reject classifies the whole package directory, not only
  `manifest.json`.
- Receipts record package inventory and content hashes.
- Active P5 governance changelog entries must be accepted or explicitly
  superseded by accepted P5.1 entries.
- Normal orchestrator conveyor flow should consume ASO status/receipt summaries
  before rereading broad governance documents.

## Non-Goals

P5.1 does not add a daemon, live dispatch executor, checkpoint executor,
ASO Studio, product-intake engine, distributed workers, secret collection, or
automatic task execution.

## Filesystem Boundary

The ASO package may track package files under `README.md`,
`README_INSTALL.md`, `.github/workflows/`, `pyproject.toml`, and
`agent-system/`.

The following roots remain forbidden as tracked package files:

```text
project-input/
project-runtime/
project-archive/
.venv/
```
