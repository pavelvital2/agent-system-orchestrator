# STAGE3_SAFE_AUTOMATION_DIAGNOSTICS_COMMANDS

## Purpose

This example records the Stage 3 ASO command expectations for package users and
auditors. It is documentation only and does not grant any automation authority.

## Version tuple

```text
CURRENT_PACKAGE_VERSION: 3.1.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.1.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
```

## Direct script baseline

Direct script execution remains the compatibility baseline for package checks:

```text
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py --help
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py package-sync verify --root . --strict
```

## Installed command expectation

The installed console command is additive after local editable install:

```text
python3 -m pip install -e .
aso --help
aso package-sync verify --root . --strict
```

Package documentation and validation evidence should continue to include direct
script commands so fresh checkouts can validate the package before installing
the console script.

## Safety boundary

Stage 3 command surfaces are read-only, dry-run, or proposal-only. They may
inspect package metadata, rule documentation, release notes, and cleanup
eligibility. They must not:

- dispatch agents;
- mutate package or workspace state;
- repair files silently;
- execute governed checkpoints;
- approve owner decisions;
- stage, commit, push, or tag;
- publish local `project-input/`, `project-runtime/`, or `project-archive/`
  material.

`package-sync verify` is a guard. A strict mismatch is a blocker for audit or
release acceptance until a bounded correction task resolves the drift.
