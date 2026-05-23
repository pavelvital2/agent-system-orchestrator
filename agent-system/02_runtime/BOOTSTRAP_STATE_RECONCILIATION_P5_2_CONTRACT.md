# BOOTSTRAP_STATE_RECONCILIATION_P5_2_CONTRACT

## Version Boundary

P5.2 is the bootstrap state reconciliation correction for the ASO package.

```text
PACKAGE_VERSION: 3.7.2
GOVERNANCE_RULESET_VERSION: 3.7.2
RUNTIME_SCHEMA_VERSION: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
```

Runtime Schema `3.1.0` and Artifact Package Schema `1.1.0` are preserved.
P5.2 changes validation and planning semantics for contradictory bootstrap
state only; it does not redefine the sidecar envelope.

## Correction Contract

The following bootstrap tuple is invalid unless a separate documented terminal
bootstrap invariant is present:

```text
CURRENT_PHASE: bootstrap
PROJECT_STATUS: active
CURRENT_GATE.STATUS: open
NEXT_ACTION.ACTION_SEMANTIC: stop_terminal
```

When mandatory bootstrap inputs exist and first profile-agent dispatch has not
occurred, the orchestrator and `plan-next` must route to bootstrap preparation
or governed correction. They must not report ready terminal STOP.

`PROJECT_STATE.TZ_PATH` is a path field. If `project-input/TZ.md` exists, the
field must reference that file or another valid project TZ file path. It must
not contain an IANA timezone string such as `Europe/Moscow`.

Markdown runtime views derived from `project-runtime/state/*.json` must be
materialized before strict workspace checks report clean readiness. Missing
derived views are repairable blockers; strict status, lint, doctor, and state
verification must either materialize them through an explicit render command or
return an actionable repair route.

## Conveyor Alignment

Normal orchestration remains a reduced conveyor over ASO status/next summaries,
validation reports, receipts, and explicit task packets. The conveyor may use
summaries for routine routing, but summaries cannot override sidecar semantics.
If summaries contradict bootstrap state, terminal action, or required view
materialization, the orchestrator must stop normal flow and enter recovery or
correction routing.

## Non-Goals

P5.2 does not add a daemon, live dispatch executor, checkpoint executor,
ASO Studio, product-intake engine, product generator, distributed workers,
secret collection, semantic raw-TZ interpretation, or automatic task
execution.

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
