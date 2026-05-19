# STAGE3_SAFE_AUTOMATION_DIAGNOSTICS_RELEASE_NOTES

## Scope

Stage 3 updates package documentation, metadata, command examples, Makefile
coverage, changelog traceability, and release cleanup notes for:

```text
CURRENT_PACKAGE_VERSION: 3.1.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.1.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

The runtime schema remains `3.0.0`. Stage 3 is a compatible diagnostics and
release cleanup update, not a runtime-state migration.

## ASO safety boundary

Stage 3 ASO command surfaces are read-only, dry-run, or proposal-only. The
package-sync guard verifies metadata and command surface coherence. It does not
repair files, dispatch agents, mutate package or workspace state, run governed
checkpoints, approve owner decisions, stage changes, commit, push, tag, or
publish local evidence roots.

## Command surface

Direct script execution remains the compatibility baseline:

```text
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py --help
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py package-sync verify --root . --strict
```

The installed console command remains additive after editable install:

```text
python3 -m pip install -e .
aso --help
aso package-sync verify --root . --strict
```

## Historical evidence

Previous release evidence remains historical and must not be rewritten as Stage
3 final evidence:

```text
agent-system/11_release/STAGE1_UPGRADE_VALIDATION_REPORT.md
agent-system/11_release/STAGE2_UPGRADE_VALIDATION_REPORT.md
agent-system/11_release/STAGE2_STATE_CONTRACT_CORRECTION_VALIDATION_REPORT.md
```

## Task 008 boundary

This file is Task 007 documentation and release cleanup evidence only. It does
not claim final Stage 3 validation pass. Task 008 must supply the final command
evidence before any final validation or acceptance claim is made.

The standalone governance smoke runner contains its own fixture expectations
and must be aligned with the active Stage 3 tuple before it can serve as final
Stage 3 acceptance evidence. Task 007 keeps `make smoke` focused on the
read-only ASO diagnostics that are within this task's write scope.

## Publication cleanup boundary

`project-input/`, `project-runtime/`, and `project-archive/` are local
generated or owner-input roots. They are not accepted package documentation and
must not be staged, committed, pushed, tagged, or published as release evidence.
Stable Stage 3 summaries belong under accepted package paths such as
`agent-system/11_release/`.
